import matplotlib.pyplot as plt
import numpy as np

# --- 1. CONFIGURACIÓN DE DATOS ---
# Etiquetas de las pruebas
labels = ['Medición 2', 'Medición 1']

# Valores medios obtenidos
hfe_measured = [344.09, 348.81]

# Incertidumbres (barras de error)
hfe_errors = [32.87, 102.13]

# Datos de la hoja de fabricante (Datasheet)
hfe_min = 200
hfe_typ = 290
hfe_max = 450

# --- 2. CREACIÓN DEL GRÁFICO ---
fig, ax = plt.subplots(figsize=(10, 5))

# Posiciones en el eje Y
y_pos = np.arange(len(labels))

# Dibujar los puntos con sus barras de error (xerr para horizontal)
ax.errorbar(hfe_measured, y_pos, xerr=hfe_errors, fmt='o', color='#1f77b4', 
            markersize=8, capsize=6, elinewidth=2, label='HFE Medido ($\pm$ Incertidumbre)')

# --- 3. LÍNEAS DE REFERENCIA DEL FABRICANTE ---
# Líneas verticales para los límites
ax.axvline(hfe_max, color='red', linestyle='--', alpha=0.6, label=f'Máximo Fabricante ({hfe_max})')
ax.axvline(hfe_min, color='red', linestyle='--', alpha=0.6, label=f'Mínimo Fabricante ({hfe_min})')
ax.axvline(hfe_typ, color='green', linestyle='-', alpha=0.8, label=f'Típico Fabricante ({hfe_typ})')

# Sombreado del rango aceptable
ax.fill_betweenx([-0.5, 1.5], hfe_min, hfe_max, color='gray', alpha=0.1, label='Rango Operativo Nominal')

# --- 4. FORMATO Y ESTÉTICA ---
ax.set_yticks(y_pos)
ax.set_yticklabels(labels)
ax.set_xlabel('Ganancia de Corriente ($h_{FE}$)', fontsize=12)
ax.set_title('Validación de Mediciones frente a Datasheet', fontsize=14, pad=15)
ax.set_ylim(-0.5, 1.5) # Ajusta el espacio vertical
ax.set_xlim(0, 550)    # Ajusta el rango visible del eje X

# Cuadrícula suave
ax.grid(True, linestyle='--', alpha=0.5)

# Leyenda
ax.legend(loc='upper left', frameon=True, shadow=True)

# Ajuste automático de márgenes
plt.tight_layout()

# --- 5. MOSTRAR O GUARDAR ---
# plt.savefig('mi_grafico_hfe.png', dpi=300) # Descomenta para guardar como imagen
plt.show()