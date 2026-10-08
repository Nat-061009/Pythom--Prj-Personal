// Describe cada entidad, el texto visible y los campos que aparecen en su formulario.
const entities = {
  persona: { label: 'Personas', fields: ['cedula', 'nombre', 'apellido', 'telefono', 'correo'] },
  cliente: { label: 'Clientes', fields: ['cedula', 'fecha_registro'] },
  tienda: { label: 'Tiendas', fields: ['identificador', 'nombre', 'direccion', 'telefono'] },
  trabajador: { label: 'Trabajadores', fields: ['cedula', 'puesto', 'salario', 'tienda_id'] },
  peluche: { label: 'Peluches', fields: ['identificador', 'descripcion', 'precio', 'tamano', 'coleccion', 'imagen'] },
  factura: { label: 'Facturas', fields: ['identificador', 'fecha', 'cliente_cedula', 'trabajador_cedula', 'tienda_id', 'peluche_id', 'cantidad', 'total'] }
};

let current = 'persona';
let editing = null;
let loadedRows = [];

const pk = entity => entities[entity].fields[0];
const $ = id => document.getElementById(id);

function label(text) {
  return text.replaceAll('_', ' ');
}

function inputType(field) {
  if (field === 'fecha' || field === 'fecha_registro') return 'type="date"';
  if (/precio|salario|total|cantidad/.test(field)) return 'type="number" step="0.01"';
  if (field === 'correo') return 'type="email"';
  if (field === 'imagen') return 'type="file" accept="image/*"';
  return '';
}

function fieldInput(field) {
  const readonly = field === pk(current) && editing ? 'readonly' : '';
  const required = field === 'imagen' ? '' : 'required';
  return `<label>${label(field)}<input name="${field}" ${readonly} ${inputType(field)} ${required}></label>`;
}

function imageCell(value) {
  if (!value) return '';
  return `<img class="thumb" src="${value}" alt="Imagen del peluche">`;
}

function cellValue(field, value) {
  if (field === 'imagen') return imageCell(value);
  return value ?? '';
}

function readImage(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

function nav() {
  $('tabs').innerHTML = Object.entries(entities).map(([key, value]) =>
    `<button class="${key === current ? 'active' : ''}" onclick="choose('${key}')">${value.label}</button>`
  ).join('');
}

function choose(entity) {
  current = entity;
  editing = null;
  nav();
  render();
  load();
}

function render() {
  const entity = entities[current];
  $('title').textContent = entity.label;
  $('message').textContent = '';
  $('form').innerHTML = entity.fields.map(fieldInput).join('') +
    `<button class="primary">${editing ? 'Actualizar' : 'Crear'}</button>`;
  $('form').onsubmit = save;
  $('head').innerHTML = '<tr>' + entity.fields.map(field => `<th>${label(field)}</th>`).join('') + '<th>Acciones</th></tr>';
}

async function load() {
  const response = await fetch('/api/' + current);
  loadedRows = await response.json();
  $('body').innerHTML = loadedRows.map((row, index) => '<tr>' +
    entities[current].fields.map(field => `<td>${cellValue(field, row[field])}</td>`).join('') +
    `<td class="actions"><button onclick="edit(${index})">Editar</button><button class="danger" onclick="removeRow('${row[pk(current)]}')">Borrar</button></td></tr>`
  ).join('');
}

async function save(event) {
  event.preventDefault();
  const formData = new FormData(event.target);
  const data = {};

  for (const field of entities[current].fields) {
    if (field === 'imagen') {
      const file = formData.get(field);
      data[field] = editing?.imagen || '';
      if (file && file.size > 0) {
        if (!file.type.startsWith('image/')) {
          $('message').textContent = 'Selecciona un archivo de imagen.';
          return;
        }
        if (file.size > 2 * 1024 * 1024) {
          $('message').textContent = 'La imagen debe pesar menos de 2 MB.';
          return;
        }
        data[field] = await readImage(file);
      }
      continue;
    }
    data[field] = formData.get(field);
  }

  for (const field of entities[current].fields) {
    if (/precio|salario|total/.test(field)) data[field] = Number(data[field]);
    if (field === 'cantidad') data[field] = Number.parseInt(data[field], 10);
  }
  const url = '/api/' + current + (editing ? '/' + data[pk(current)] : '');
  const response = await fetch(url, {
    method: editing ? 'PUT' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!response.ok) {
    $('message').textContent = (await response.json()).detail;
    return;
  }
  $('message').textContent = 'Guardado correctamente.';
  editing = null;
  render();
  load();
}

function edit(index) {
  editing = loadedRows[index];
  render();
  for (const [key, value] of Object.entries(editing)) {
    if ($('form').elements[key]?.type !== 'file') $('form').elements[key].value = value;
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function removeRow(key) {
  if (!confirm('Eliminar este registro?')) return;
  const response = await fetch('/api/' + current + '/' + key, { method: 'DELETE' });
  $('message').textContent = response.ok ? 'Registro eliminado.' : (await response.json()).detail;
  load();
}

nav();
render();
load();
