# Zoho Inventory Analyst Pro

Una poderosa aplicacion de escritorio desarrollada en Python que permite gestionar y analizar el inventario de Zoho Books de manera eficiente con una interfaz moderna.

## Caracteristicas

- **Visualizacion del Inventario**: Muestra todos los productos/articulos de Zoho en una tabla interactiva con informacion clave incluyendo nombre, SKU, marca, stock y estado.
- **Busqueda en Tiempo Real**: Filtra productos instantaneamente por nombre o SKU mientras escribes.
- **Temas Multiples**: Elige entre los temas Cool Pastel, Warm Pastel o Oscuro.
- **Detalles Completos**: Al seleccionar un producto, puedes ver:

  - Stock fisico vs contable
  - Historial de compras y ventas (cantidades y montos)
  - Ordenes de venta recientes
  - Ordenes de compra recientes
  - Facturas asociadas
  - Facturas de compra asociadas

- **Gestion de Estados**: Activa o desactiva productos directamente desde la aplicacion.
- **Edicion de Descripciones**: Edita las descripciones de venta y compra de los productos.
- **Bloqueo de Descripciones**: Bloquea las descripciones para evitar ediciones accidentales.
- **Vincular Descripciones**: Sincroniza automaticamente las descripciones de venta y compra.
- **Integracion de Busqueda Web**: Inicia busquedas de productos en multiples proveedores:

  - Google Search
  - Google AI Search
  - Zoro
  - Grainger
  - eBay
  - Amazon
  - Eaton
  - Tequipment
  - Lowe's

- **Historial de Busquedas**: Ver y repetir busquedas anteriores.
- **Sincronizacion en Segundo Plano**: La aplicacion sincroniza con Zoho sin congelarse, usando un sistema de cache local.
- **Cache Local**: Los datos se almacenan en SQLite para carga instantanea.
- **Registro de Actividad**: Todas las acciones se registran para seguimiento.
- **Edicion de Marcas**: Actualiza la marca de los productos directamente.
- **Proteccion con Contrasena**: La aplicacion puede protegerse con una contrasena.

## Requisitos

- Python 3.8+
- Cuenta de Zoho Books con acceso a API
- Credenciales OAuth2 de Zoho
- Paquetes requeridos: `requests`, `python-dotenv`, `PyQt6`

## Instalacion

1. Clona este repositorio:
```bash
git clone https://github.com/your-repo/zoho_inventory_app.git
cd zoho_inventory_app
```

2. Instala las dependencias:
```bash
pip install requests python-dotenv PyQt6
```

3. Configura tus credenciales de Zoho en el archivo `.env`:
```
ZOHO_CLIENT_ID=your_client_id
ZOHO_CLIENT_SECRET=your_client_secret
ZOHO_REFRESH_TOKEN=your_refresh_token
ZOHO_ORG_ID=your_organization_id
```
### Alternativamente
Descarga el ultimo archivo ejecutable en la seccion de publicaciones (https://github.com/ibistetvaga/Zoho-Inventory-Manager/releases/tag/Prototype)

## Como Obtener Credenciales de Zoho

1. Inicia sesion en [Zoho Books](https://books.zoho.com)
2. Abre la Consola de API de Zoho
3. Crea un nuevo cliente OAuth (Self-Client)
4. Genera un Codigo de Permiso (Scopes: ZohoBooks.items.CREATE, ZohoBooks.items.READ, ZohoBooks.items.UPDATE, ZohoBooks.salesorders.READ, ZohoBooks.purchaseorders.READ, ZohoBooks.invoices.READ, ZohoBooks.bills.READ, ZohoBooks.settings.READ, ZohoBooks.settings.CREATE, ZohoBooks.settings.UPDATE)
5. Copia el Client ID y Client Secret
6. Usa el script `one-time.py` para obtener el Refresh Token (necesitas el codigo de autorizacion)

## Uso (correr desde el codigo fuente)

Ejecuta la aplicacion:
```bash
python main.py
```

### Controles:

- **Barra de Busqueda**: Escribe para filtrar productos por nombre o SKU
- **Actualizar Datos**: Fuerza una sincronizacion completa con Zoho
- **Doble clic en un producto**: Muestra detalles completos
- **Boton Activar/Desactivar**: Cambia el estado del producto en Zoho
- **Iniciar Busqueda**: Abre busquedas de productos en tu navegador predeterminado
- **Guardar Descripciones**: Guarda las descripciones de venta/compra editadas
- **Editar Marca**: Actualiza la marca del producto

### Opciones del Menu:

- **Archivo > Actualizar Todo**: Sincroniza todos los datos con Zoho (F5)
- **Archivo > Salir**: Cierra la aplicacion
- **Configuracion > Fuentes de Busqueda**: Configura que motores de busqueda usar
- **Configuracion > Cambiar Contrasena**: Cambia la contrasena de la aplicacion
- **Ver > Tema**: Cambia entre Cool Pastel, Warm Pastel y Oscuro
- **Ver > Ver Registro de Actividad**: Ver el archivo de registro de actividad
- **Ver > Historial de Busquedas**: Ver y gestionar busquedas pasadas

## Scripts Adicionales

### extagnant.py
Encuentra articulos que nunca aparecen en ningun documento y los exporta a Excel/JSON. Util para identificar inventario obsoleto.

```bash
python extagnant.py --reset        # Reiniciar base de datos y comenzar de cero
python extagnant.py --output items.xlsx  # Archivo de salida personalizado
```

### mark_inactive.py
Marca articulos como inactivos en Zoho Books basandose en la salida JSON de extagnant.py.

```bash
python mark_inactive.py --input items_sin_documentos.json
python mark_inactive.py --dry-run    # Vista previa sin hacer cambios
python mark_inactive.py --skip-existing  # Saltar articulos ya inactivos
```

## Estructura del Proyecto

```
zoho_inventory_app/
├── main.py               # Aplicacion GUI principal (PyQt6)
├── zoho_api.py           # Cliente API y gestion de cache
├── browser_search.py     # Integracion de busqueda web
├── history_manager.py    # Gestion del historial de busquedas
├── config_manager.py     # Gestion de configuracion
├── threads.py            # Clases QThread para operaciones en segundo plano
├── dialogs.py            # Dialogos de la aplicacion
├── secure_config.py      # Gestion de contrasenas seguras
├── utils.py              # Utilidades varias
├── paths.py              # Gestion de rutas de archivos
├── extagnant.py          # Encuentra articulos sin documentos
├── mark_inactive.py      # Marca articulos como inactivos por lotes
├── one-time.py           # Script para obtener refresh token
├── config.json           # Configuracion de la aplicacion (auto-creado)
├── activity.log          # Registro de actividad (auto-creado)
├── .env                  # Credenciales (no compartir)
├── .gitignore            # Reglas de ignorados de Git
├── inventory.db          # Cache de SQLite (auto-creado)
├── inventory_full.db     # Base de datos completa con documentos (auto-creado)
├── README.md             # Este archivo
└── TECHNICAL_GUIDE.md    # Documentacion tecnica
```

## Detalles Tecnicos

### Arquitectura

1. **Capa de Interfaz (main.py)**
   - Usa PyQt6 para la GUI de escritorio
   - Implementa hilos para que la UI no se congele durante llamadas a la API
   - Usa senales para comunicacion segura entre hilos

2. **Capa de Logica de Negocio (zoho_api.py)**
   - `ZohoClient`: Maneja toda la comunicacion con la API de Zoho Books
   - `LocalCache`: Almacena datos en una base de datos SQLite local

3. **Integracion de Busqueda (browser_search.py)**
   - Abre busquedas de productos en el navegador predeterminado
   - Soporta multiples fuentes de busqueda

4. **Gestion de Historial (history_manager.py)**
   - Almacena el historial de busquedas en formato JSON
   - Soporta respaldo y restauracion
   - Soporta exportacion e importacion

5. **Gestion de Configuracion (config_manager.py)**
   - Maneja la configuracion de fuentes de busqueda y temas
   - Almacena en archivo JSON

6. **Seguridad (secure_config.py)**
   - Protege la aplicacion con contrasena
   - Almacena credenciales de forma segura

### API de Zoho Books v3

La aplicacion usa estos endpoints:
- `GET /items` - Obtener todos los productos
- `GET /items/{id}` - Obtener detalles del producto
- `PUT /items/{id}` - Actualizar producto (descripciones, marca)
- `POST /items/{id}/active` - Activar producto
- `POST /items/{id}/inactive` - Desactivar producto
- `GET /salesorders?item_id={id}` - Ordenes de venta del producto
- `GET /purchaseorders?item_id={id}` - Ordenes de compra del producto
- `GET /invoices?item_id={id}` - Facturas del producto
- `GET /bills?item_id={id}` - Facturas de compra del producto

## Notas Importantes

- **Seguridad**: Nunca compartas tu archivo `.env` ni subas credenciales al repositorio.
- **Limites de API**: Zoho tiene limites de llamadas a la API (10000 usos al dia). La aplicacion implementa cache para minimizar llamadas.
- **Tokens**: Los tokens de acceso expiran. El codigo maneja automaticamente el refresco de tokens.
- **Base de Datos**: `inventory.db` contiene datos en cache para carga rapida. `inventory_full.db` es usado por extagnant.py para analisis completo.
- **Contrasena**: La primera vez que ejecutes la aplicacion, se pedira configurar una contrasena. Esta contrasena se almacenara de forma segura y se requerira en cada inicio.

---

Desarrollado usando Python, PyQt6 y Zoho Books API
