import os
import subprocess
import shutil
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import pandas as pd
import sys

def generar_pdf_final(temperatura=25.0, humedad=55.0, modelo_transistor="BC547"):
    # Obtener la fecha actual formateada    
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    now = datetime.now()
    fecha_espanol = f"{now.day} de {meses[now.month - 1]} de {now.year}"

    # 1. Configuración de carpetas y nombres
    directorio_root = os.getcwd()
    directorio_aux = os.path.join(directorio_root, "aux_files")
    
    if not os.path.exists(directorio_aux):
        os.makedirs(directorio_aux)

    # Archivos necesarios en la raíz
    archivo_logo = "pictures/logo_institucion.png"

    # Rutas Base (Asumiendo carpeta Test1)
    # Nota: Es mejor pasar la ruta del proyecto como argumento a la función.
    path_salida = "Test1/Salida"
    path_entrada = "Test1/Entrada"

    # Definición de archivos esperados (Usamos .get para evitar errores si no existen)
    plots = {
        "salida_ic": os.path.join(path_salida, "curva_IC_vs_VCE.png"),
        "salida_ib": os.path.join(path_salida, "curva_IB_vs_VCE.png"),
        "entrada_ib": os.path.join(path_entrada, "curva_IB_vs_VBE.png"),
        "entrada_hfe": os.path.join(path_entrada, "curva_HFE_vs_IC.png"),
        "entrada_trans": os.path.join(path_entrada, "curva_IC_vs_VBE.png"),
        "entrada_vbe_ic": os.path.join(path_entrada, "curva_VBE_vs_IC.png")
    }
    
    # Validar logo (lo único crítico para el header)
    if not os.path.exists(archivo_logo):
        print(f"Warning: Falta logo en {archivo_logo}")

    # 2. Configuración de Jinja2
    env = Environment(
        loader=FileSystemLoader(directorio_root),
        block_start_string='\\BLOCK{',
        block_end_string='}',
        variable_start_string='((',
        variable_end_string='))'
    )
    
    # ... Inicialización de variables para el contexto
    tabla_salida_latex = ""
    tabla_entrada_latex = ""
    show_salida = False
    show_entrada = False

    # --- INTENTO DE LEER TEMPERATURA REAL DEL CSV CRUDO ---
    # Buscamos el archivo crudo 'salida.csv' que tiene los datos del sensor
    try:
        raw_csv = os.path.join(path_salida, "salida.csv")
        if os.path.exists(raw_csv):
            # Leemos solo las primeras filas o todo para sacar el promedio
            df_raw = pd.read_csv(raw_csv, comment='#')
            
            # Buscamos columnas que contengan "Temp" y "Hum" (flexible por si cambias nombres)
            col_t = next((c for c in df_raw.columns if "Temp" in c), None)
            col_h = next((c for c in df_raw.columns if "Hum" in c), None)
            
            if col_t and col_h:
                # Convertimos a numérico forzando errores a NaN y sacamos promedio
                t_prom = pd.to_numeric(df_raw[col_t], errors='coerce').mean()
                h_prom = pd.to_numeric(df_raw[col_h], errors='coerce').mean()
                
                # Actualizamos las variables si los datos son válidos
                if pd.notna(t_prom): temperatura = round(t_prom, 1)
                if pd.notna(h_prom): humedad = round(h_prom, 1)
    except Exception as e:
        print(f"No se pudo leer temperatura/humedad del CSV raw: {e}")

    try:
        # --- PROCESAR SALIDA ---
        csv_salida = os.path.join(path_salida, "salida_fisica.csv")
        
        # Inicializamos vacía
        tabla_salida_latex = ""

        if os.path.exists(csv_salida):
            df_s = pd.read_csv(csv_salida)
            show_salida = True
            
            # Detectamos la columna de agrupación (generalmente "Indice" o "IB_uA")
            # Usamos "Indice" para iterar ordenadamente por curva
            if "Indice" in df_s.columns:
                puntos_tabla = []
                for nombre_grupo, grupo in df_s.groupby("Indice"):
                    # Tomamos 3 puntos representativos: Inicio, Medio, Fin
                    indices = [0, len(grupo)//2, len(grupo)-1]
                    puntos_tabla.append(grupo.iloc[indices])
                
                df_red_s = pd.concat(puntos_tabla)
                
                # Definimos qué columnas mostrar y sus nombres bonitos en LaTeX
                cols_map_s = {
                    'IB_uA': r'$I_B [\mu A]$',      # Parámetro de la curva
                    'U_IB_uA': r'$\pm U(I_B) [\mu A]$', # Parámetro de la curva
                    'VCE_V': r'$V_{CE} [V]$',       # Eje X
                    'U_VCE_V': r'$\pm U(V_{CE}) [V]$',  # Incertidumbre del eje X
                    'IC_mA': r'$I_C [mA]$',         # Eje Y
                    'U_IC_mA': r'$\pm U(I_C) [mA]$' # Incertidumbre del eje y
                }
                
                # Filtramos solo las que existen en el CSV
                cols_existentes = [c for c in cols_map_s.keys() if c in df_s.columns]
                df_final_s = df_red_s[cols_existentes].rename(columns=cols_map_s)
                
                # Generamos el código LaTeX
                tabla_salida_latex = df_final_s.to_latex(
                    index=False, float_format="%.2f", column_format='|c|c|c|c|c|c|', escape=False
                ).replace('\\\\\n', '\\\\ \\hline\n')
        
        # --- PROCESAR ENTRADA ---
        csv_entrada = os.path.join(path_entrada, "entrada_fisica.csv")
        
        # Inicializamos vacías por si no entra al if
        tabla_entrada_vi_latex = ""
        tabla_entrada_hfe_latex = ""

        if os.path.exists(csv_entrada):
            df_e = pd.read_csv(csv_entrada)
            show_entrada = True
            
            # Reducción de puntos (para que entre en la hoja)
            n = len(df_e)
            if n > 15: # Un poco más de puntos si dividimos tablas
                indices = [int(i) for i in range(0, n, n//15)]
                df_red_e = df_e.iloc[indices]
            else:
                df_red_e = df_e

            # TABLA 1: Características V/I (primeros 3 gráficos)
            cols_map_vi = {
                'VBE_V': r'$V_{BE} [V]$',
                'U_VBE_V': r'$\pm U_(V_{BE}) [V]$', 
                'IB_uA': r'$I_B [\mu A]$', 
                'U_IB_uA': r'$\pm U(I_B) [\mu A]$', 
                'IC_mA': r'$I_C [mA]$',
                'U_IC_mA': r'$\pm $U(I_C) [mA]$'
            }
            # Filtramos solo esas columnas
            cols_existentes_vi = [c for c in cols_map_vi.keys() if c in df_e.columns]
            df_vi = df_red_e[cols_existentes_vi].rename(columns=cols_map_vi)

            tabla_entrada_vi_latex = df_vi.to_latex(
                index=False, float_format="%.3f", column_format='|c|c|c|c|c|c|', escape=False
            ).replace('\\\\\n', '\\\\ \\hline\n')

            # TABLA 2: Solo para HFE
            cols_map_hfe = {
                'IC_mA': r'$I_C [mA]$',
                'U_IC_mA': r'$\pm U(I_C) [mA]$',
                'HFE': r'$H_{FE} [-]$',
                'U_HFE': r'$\pm U(H_{FE} [-])$'
            }
            # Filtramos solo esas columnas
            cols_existentes_hfe = [c for c in cols_map_hfe.keys() if c in df_e.columns]
            df_hfe = df_red_e[cols_existentes_hfe].rename(columns=cols_map_hfe)

            tabla_entrada_hfe_latex = df_hfe.to_latex(
                index=False, float_format="%.2f", column_format='|c|c|c|c|', escape=False
            ).replace('\\\\\n', '\\\\ \\hline\n')

    except Exception as e:
        print(f"Error procesando datos CSV: {e}")

    try:
        
        template = env.get_template('plantilla.tex')
        
        contexto = {
            "titulo": "INFORME TÉCNICO DE LABORATORIO",
            "subtitulo": "Sistema de Adquisición de Datos",
            "modelo": modelo_transistor,
            "tipo": "Caracterización de Transistores",
            "fecha": fecha_espanol,
            "logo_path": os.path.abspath(archivo_logo).replace('\\', '/'),
            "temperatura": str(temperatura),
            "humedad": str(humedad),
            "tecnicos": [
                {"nombre": "Octavio Puz", "contacto": "opuzbattellini@frba.utn.edu.ar"},
                {"nombre": "Guido Spataro", "contacto": "gspatarosaponara@frba.utn.edu.ar"},
                {"nombre": "Ruiz Brisa", "contacto": "brruiz@frba.utn.edu.ar"},
                {"nombre": "Franco Mendez", "contacto": "fmendez@frba.utn.edu.ar"},
                {"nombre": "Agustín Longo", "contacto": "alognoflorean@frba.utn.edu.ar"},
            ],
            # Variables de control
            "show_salida": show_salida,
            "show_entrada": show_entrada,
            # Gráficos
            "plot_salida_ic": os.path.abspath(plots["salida_ic"]).replace('\\', '/'),
            "plot_salida_ib": os.path.abspath(plots["salida_ib"]).replace('\\', '/') if os.path.exists(plots["salida_ib"]) else None,
            "plot_entrada_ib": os.path.abspath(plots["entrada_ib"]).replace('\\', '/'),
            "plot_entrada_hfe": os.path.abspath(plots["entrada_hfe"]).replace('\\', '/'),
            "plot_entrada_trans": os.path.abspath(plots["entrada_trans"]).replace('\\', '/'),
            "plot_entrada_vbe_ic": os.path.abspath(plots["entrada_vbe_ic"]).replace('\\', '/'),
            # Tablas
            "tabla_salida": tabla_salida_latex,
            "tabla_entrada_vi": tabla_entrada_vi_latex,
            "tabla_entrada_hfe": tabla_entrada_hfe_latex
        }

        # 3. Generar el archivo .tex dentro de la carpeta aux
        output_tex_name = "informe_compilado.tex"
        output_tex_path = os.path.join(directorio_aux, output_tex_name)
        
        with open(output_tex_path, 'w', encoding='utf-8') as f:
            f.write(template.render(contexto))

        # 4. Compilación: Entramos a la carpeta aux para ejecutar pdflatex
        print("Compilando informe...")
        os.chdir(directorio_aux) # CAMBIO DE DIRECTORIO TEMPORAL
        
        startup_flags = 0
        if os.name == 'nt': # Solo en Windows
            startup_flags = subprocess.CREATE_NO_WINDOW

        for i in range(2):
            # Al estar ya dentro de aux_files, no necesitamos -output-directory
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', output_tex_name],
                capture_output=True,
                text=True,
                creationflags=startup_flags
            )

        # Volvemos a la raíz
        os.chdir(directorio_root)
        nombre_informe = f"Informe-Final-{now.day:02d}-{now.month:02d}-{now.year}_{now.hour:02d}-{now.minute:02d}.pdf"
        # 5. Mover el PDF resultante a la raíz
        pdf_generado = os.path.join(directorio_aux, "informe_compilado.pdf")
        if os.path.exists(pdf_generado):
            ruta_carpeta_informes = os.path.join(directorio_root, "informes")
            if not os.path.exists(ruta_carpeta_informes):
                os.makedirs(ruta_carpeta_informes)
            ruta_destino_final = os.path.join(ruta_carpeta_informes, nombre_informe)
            shutil.copy(pdf_generado, f'informes/{nombre_informe}')
            print(f">>> Éxito: {nombre_informe} generado en la carpeta principal.")
        else:
            print(">>> Error en la compilación de LaTeX. Log del error:")
            print(result.stdout) # Muestra el error de LaTeX si falló


    except Exception as e:
        # Asegurarse de volver a la raíz si algo falla
        os.chdir(directorio_root)
        print(f"Error en el script: {e}")

if __name__ == "__main__":
    # Llamada simple segura para pruebas directas o desde mainwindow
    modelo_arg = sys.argv[1] if len(sys.argv) > 1 else "BC547"
    generar_pdf_final(modelo_transistor=modelo_arg)