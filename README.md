# Sistema Unidad Territorial

## Descripción general

**Sistema Unidad Territorial** es una aplicación orientada a mejorar la gestión administrativa y operativa de una **junta de vecinos**. Surge ante la necesidad de modernizar procesos que, tradicionalmente, se realizan de manera manual o fragmentada, como la inscripción de vecinos, la emisión de certificados de residencia y la organización de proyectos comunitarios. 

El sistema busca **centralizar y automatizar** estas funciones, facilitando la interacción entre los habitantes y el directorio de la junta de vecinos, con un enfoque en usabilidad y accesibilidad.
Actualmente el proyecto se encuentra en fase inicial, con un modelo de base de datos definido y endpoints básicos de autenticación de administrador.

*⚠️ **Estado actual:** El proyecto aún se encuentra en desarrollo activo, por lo que pueden existir **cambios frecuentes en la estructura, dependencias y funcionalidades**.*

## Características

- **Inscripción de vecinos** mediante formulario digital.  
- **Emisión de certificados de residencia** en formato digital, previa revisión/aprobación.  
- **Postulación y gestión de proyectos vecinales**, con notificación automática de resultados.  
- **Sistema de notificaciones** (afiches, correo electrónico y WhatsApp).  
- **Calendario de reservas** de espacios comunitarios (canchas, salas, plazas).  
- **Gestión de actividades** y control de cupos de participación.  
- **Publicación de noticias** relevantes para la comunidad.  

## Tecnologías utilizadas

- **Back-end:** [FastAPI](https://fastapi.tiangolo.com/)  
- **Front-end:** [Angular](https://angular.io/)  
- **Base de datos:** [PostgreSQL](https://www.postgresql.org/)  
- **Gestión de dependencias:** [Poetry](https://python-poetry.org/)  
- **Autenticación:** OAuth 2.0 con Google  
- **Otros:** Docker (opcional), Git, integración con servicios de correo y WhatsApp.  

## Requisitos de instalación

Antes de instalar, asegúrese de contar con:

1. **Python 3.10+** y **Poetry** instalados.  
2. **Node.js** (≥14) y [Angular CLI](https://angular.io/cli).  
3. **PostgreSQL** configurado con base de datos y usuario válido.  
4. (Opcional) **Docker** para orquestar servicios.

### Backend (FastAPI)

1. Instalar dependencias con Poetry:

   ```bash
   poetry install

2. Configurar variables de entorno en un archivo `.env`. Ejemplo:

   ```env
   ENVIRONMENT=DEVELOPMENT
   SECRET_KEY=EJEMPLO_ClaveSecretaSegura123
   GOOGLE_OAUTH_CLIENT_ID=EJEMPLO_tu_client_id.apps.googleusercontent.com
   GOOGLE_OAUTH_CLIENT_SECRET=EJEMPLO_tu_client_secret
   GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
   ```

3. Inicializar la base de datos con Alembic u otra herramienta de migraciones.

4. Ejecutar el servidor:

   ```bash
   poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000 --log-level info
   ```

   El backend quedará disponible en `http://127.0.0.1:8000/` con documentación en `http://127.0.0.1:8000/docs`.

### Frontend (Angular)

1. Instalar dependencias y levantar el servidor de desarrollo:

   ```bash
   cd frontend
   npm install
   ng serve
   ```

   Disponible en `http://localhost:4200/`.

## Instrucciones de uso

1. Clonar el repositorio.
2. Configurar `.env` en el backend y `.env` correspondiente en el frontend si aplica.
3. Ejecutar backend y frontend en paralelo.
4. Acceder a la interfaz web en `http://localhost:4200/`.
5. Usar cuentas administradoras para validar funcionalidades iniciales (autenticación y gestión básica).

## Capturas o ejemplos

*Aún no disponibles. Se agregarán imágenes y ejemplos una vez que el sistema alcance un estado funcional más avanzado.*

## Autores

* **Nicolas Lizama Millar** – [nico.lizama@duocuc.cl](mailto:nico.lizama@duocuc.cl)
* **Vincenzo Orellana Barrera** – [vin.orellana@duocuc.cl](mailto:vin.orellana@duocuc.cl)
* **Daniel Reyes Henriquez** – [dan.reyesh@duocuc.cl](mailto:dan.reyesh@duocuc.cl)

## Licencia

Este proyecto se distribuye bajo la **Apache License 2.0**.
Puedes consultar el texto completo en el archivo `LICENSE`.

