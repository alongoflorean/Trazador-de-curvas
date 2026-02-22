# Trazador de Curvas - Caracterización de Transistores BJT

## Descripción
Este proyecto es un sistema de adquisición de datos y caracterización de transistores bipolares (NPN). Cuenta con una interfaz gráfica que permite establecer comunicación serial con un microcontrolador ESP32 para automatizar el barrido de mediciones. El software procesa los datos adquiridos, calcula la ganancia de corriente ($H_{FE}$), evalúa las incertidumbres de medición y genera automáticamente un informe técnico en formato PDF.

## Características Principales
* **Interfaz Gráfica (GUI):** Desarrollada con PyQt5, incluye controles para la configuración de muestras y curvas.
* **Adquisición de Datos:** Lectura de puertos COM y comunicación serial directa con el hardware de medición.
* **Procesamiento de Incertidumbres:** Cálculo de incertidumbres para tensiones y corrientes, siguiendo los lineamientos de la GUM.
* **Visualización:** Generación automática de gráficos (IC vs VCE, IB vs VBE, HFE vs IC)
* **Reportes Automáticos:** Integración de un motor LaTeX portable para compilar informes técnicos detallados sin necesidad de dependencias externas en el sistema operativo. (se ofrecen releases más livianas sin los modulos latex incluidos)

## Ejecución de la Versión Portable

Para utilizar el software en un entorno de laboratorio sin requerir la instalación de Python ni paquetes de LaTeX en el sistema operativo:

1. Descargar o copiar la carpeta del proyecto compilado (`TrazadorDeCurvas`).
2. Abrir una terminal y navegar hasta el directorio raíz de dicha carpeta.
3. (Windows) Descomprimir archivo latex_system. Colocar la carpeta latex_system a nivel del ejecutable (al descomprimir suelen haber dos niveles con igual nombre, dejar uno solo)
4. Todo listo para ejecutar y medir.