'''
    Grupo:      N01
    Cursada:    2025
    Curso:      R4001
'''

'''
#######################################################################################

                                    IMPORTS

#######################################################################################
'''

import sys
import serial
from PyQt5.QtCore import Qt
import serial.tools.list_ports
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox,QDialog
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap
from ui_mainwindow import Ui_Form, apply_dark_theme, FolderDialog, WaitingDialog
import os
from PyQt5.QtWidgets import QFileDialog
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import my_report

import incertidumbre


DEBUGG = False
DARK_MODE = True

OK = 1
FAIL = 0

# Valores iniciales (por defecto)
Muestras = 10
Curvas = 5

'''
#######################################################################################

                                    CLASES

#######################################################################################
'''

class SerialReader(QThread):
    '''
    Clase SerialReader

    Clase que permite ocuparse de la lectura del puerto serie al establecer una conexión
    '''
    data_received = pyqtSignal(str)

    def __init__(self, serial_port):
        super().__init__()
        '''
        serial port:    numero de puerto al que nos conectamos
        running:        flag que indica cuando leer
        '''
        self.serial_port = serial_port
        self.running = True

    def run(self):
        '''
        Metodo para iniciar la escucha, si llega un dato se emite la señal data_recived
        '''
        while self.running:
            if self.serial_port.in_waiting:
                try:
                    data = self.serial_port.readline().decode(errors='ignore').strip()
                    self.data_received.emit(data)
                except Exception:
                    continue
            else:
                # Para que no consuma tanta energia se pone en reposo durante 1us cada ciclo
                self.usleep(1)

    def stop(self):
        '''
        Metodo para detener la escucha del puerto
        '''
        self.running = False
        self.wait()

class TrazadorApp(QWidget):
    # Señales para el modo auto
    sig_test_finalizado = pyqtSignal(bool)
    sig_barrido_finalizado = pyqtSignal()

    def __init__(self):
        '''
        Clase TrazadorApp

        Clase principal del proyecto, maneja el serial reader comandando las mediciones y archivos.
        '''

        '''Inicio las diferentes UI'''
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self,DEBUGG)
        self.uiFolder = FolderDialog()
        
        # VARIABLES DE CLASE
        '''

        serial port:        Puerto serie al que nos conectamos
        reader_thread:      
        save_path:          Ruta de la carpeta seleccionada   
        df:                 Data Frame que contiene todas las mediciones
        '''
        self.serial_port = None
        self.reader_thread = None
        self.proyect_path = None
        self.df = None
        self.data_send = None
        self.exit_df = None             # Data-frame en cuentas
        self.exit_path = None
        self.exit_df_fisico = None      # Data-frame en valores fisicos
        self.entry_path = None
        self.entry_df_fisico = None
        self.entry_df = None
        self.all_df = None
        self.incertidumbre = incertidumbre.UncertaintyCalculator()

        # ADS1115
        self.ADS_LSB_MV = 0.125 
        
        # INA219
        self.INA_SHUNT_LSB_MV = 0.01 
        
        # Resistencias
        self.R_SHUNT_COLECTOR = 1.0   # Ohms (La del INA219 modificado)
        self.R_SHUNT_BASE = 1000.0    # Ohms (La resistencia de base)

        # SEÑALES
        self.ui.select_folder_button.clicked.connect(self.select_folder)
        self.ui.refresh_button.clicked.connect(self.refresh_ports)
        self.ui.open_button.clicked.connect(self.open_port)
        self.ui.send_button.clicked.connect(self.send_data)
        self.ui.btn_config.clicked.connect(self.send_configuration)
        self.ui.btn_test.clicked.connect(self.realizar_test)

        # Cositas para poder ver el tiempo de medicion...perdon pero me copo
        self.ui.spin_muestras.valueChanged.connect(self.update_estimation)
        self.ui.spin_curvas.valueChanged.connect(self.update_estimation)
        self.ui.send_combo.currentTextChanged.connect(self.update_estimation)
        
        # ee
        self.refresh_count = 0
        self.ee_timer = QTimer()
        self.ee_timer.setSingleShot(True)
        self.ee_timer.timeout.connect(self.reset_ee_count)

        # Llamada inicial para que no aparezca vacio
        self.update_estimation()

        # Cuando el Test termine --> Ejecutar 'on_test_finished'
        self.sig_test_finalizado.connect(self.on_test_finished)
        
        # Cuando un Barrido termine --> Ejecutar 'on_sweep_finished'
        self.sig_barrido_finalizado.connect(self.on_sweep_finished)

        # Variable de Estado (Saber en qué paso estamos)
        self.current_state = 0  # 0:Idle, 1:Test, 2:Entrada, 3:Salida

        if DEBUGG:
            self.ui.exit_plot_button.clicked.connect(self.procesar_y_graficar_salida)
            self.ui.entry_plot_button.clicked.connect(self.procesar_y_graficar_entrada)
            self.ui.report_button.clicked.connect(self.generate_report)
        else:
            self.ui.full_report_button.clicked.connect(self.full_generate_report)

        self.refresh_ports()

        # if DEBUGG:
        os.makedirs("Resultados_Default",exist_ok=True)
        self.proyect_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resultados_Default")
        # Chequeo si ya existian carpetas de proyecto, si no existían las creo
        required_subfolders = ["Entrada", "Salida"]
        for subfolder in required_subfolders:
            subfolder_path = os.path.join(self.proyect_path, subfolder)
            if not os.path.exists(subfolder_path):
                os.makedirs(subfolder_path)
        self.ui.status_label.setText(f"Carpeta seleccionada:\n{self.proyect_path}")
        self.ui.status_label.setStyleSheet("color: green;")

        # No lo borro porque podria usarse la verdad, por comodidad me parecio un paso extra inecesario
        # else:
            # self.open_folder_dialog()


    def open_folder_dialog(self):
        ''''
        Metodo que obliga a comenzar con una carpeta seleccionada, ya sea una previamente creada o nueva
        '''
        dialog = FolderDialog()
        if dialog.exec_() == QDialog.Accepted:
            folder_name = dialog.get_result()
            if dialog.selected_path:
                self.proyect_path = dialog.selected_path
            else:
                folder_name = dialog.get_result()
                os.makedirs(folder_name,exist_ok=True)
                self.proyect_path = os.path.join(os.path.abspath(__file__), folder_name)
            # Chequeo si ya existian carpetas de proyecto, si no existían las creo
            required_subfolders = ["Entrada", "Salida"]
            for subfolder in required_subfolders:
                subfolder_path = os.path.join(self.proyect_path, subfolder)
                if not os.path.exists(subfolder_path):
                    os.makedirs(subfolder_path)
            self.ui.status_label.setText(f"Carpeta seleccionada:\n{self.proyect_path}")
            self.ui.status_label.setStyleSheet("color: green;")

    def select_folder(self):
        '''
        Metodo que permite abrir una ventana y seleccionar una carpeta donde se guardarán los archivos generados
        '''
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if folder:
            self.proyect_path = folder
            # Chequeo si ya existian carpetas de proyecto, si no existían las creo
            required_subfolders = ["Entrada", "Salida"]
            for subfolder in required_subfolders:
                subfolder_path = os.path.join(self.proyect_path, subfolder)
                if not os.path.exists(subfolder_path):
                    os.makedirs(subfolder_path)
            self.ui.status_label.setText(f"Carpeta seleccionada:\n{folder}")
            self.ui.status_label.setStyleSheet("color: green;")


    def reset_ee_count(self):
        self.refresh_count = 0

    def refresh_ports(self):
        self.refresh_count += 1
        self.ee_timer.start(10000) # (Re)inicia el contador de 10 segundos

        if self.refresh_count >= 10:
            self.reset_ee_count()
            self.show_ee_image()

        # Lógica original de puertos
        ports = serial.tools.list_ports.comports()
        self.ui.port_combo.clear()
        for port in ports:
            self.ui.port_combo.addItem(port.device)

    def show_ee_image(self):
        ee_path = os.path.join(os.path.dirname(__file__), "Pictures", "ee.png")
        if os.path.exists(ee_path):
            msg = QMessageBox(self)
            msg.setWindowTitle("Felicidades, lo encontraste   Jo   Jo   Jo!")
            pixmap = QPixmap(ee_path)
            # Escalar si es muy grande
            msg.setIconPixmap(pixmap.scaled(400, 400, Qt.KeepAspectRatio))
            msg.exec_()

    def open_port(self):
        '''
        Metodo que intenta abrir la comunicacion con un puerto COM seleccionado,
        si falla escribe mensaje de error en el label de la UI y no inicia la comunicacion 
        '''
        port_name = self.ui.port_combo.currentText()
        if not port_name:
            QMessageBox.warning(self, "Advertencia", "No hay puertos disponibles.")
            return

        try:
            self.serial_port = serial.Serial(port_name, 115200, timeout=1)
            self.ui.com_status_label.setText(f"Puerto {port_name} abierto correctamente.")
            self.ui.com_status_label.setStyleSheet("color: green;")

            # Inicia hilo de lectura
            self.reader_thread = SerialReader(self.serial_port)
            self.reader_thread.data_received.connect(self.display_received_data)
            self.reader_thread.start()

        except serial.SerialException as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el puerto:\n{e}")

    def send_data(self, comando_manual=None):
        if self.serial_port and self.serial_port.is_open:

            if comando_manual:
                self.data_send = comando_manual
            else:
                self.data_send = self.ui.send_combo.currentText()

            if self.data_send:
                try:
                    self.serial_port.write((self.data_send + '\n').encode())
                    # self.ui.status_label.setText(f"Enviado: {data}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"No se pudo enviar:\n{e}")
        else:
            QMessageBox.warning(self, "Puerto cerrado", "Primero abrí un puerto COM.")

    def display_received_data(self, data):
        if DEBUGG:
            self.ui.receive_text.append(f"> {data}")

        if data.startswith("TEST"):
            try:
                # Formato esperado: TEST,RESULTADO,HFE_VALOR
                parts = data.strip().split(',')
                if len(parts) >= 3:
                    resultado = parts[1]    # "OK" o "NOT_OK"
                    valor_HFE = parts[2]
                    
                    if resultado == "OK":
                        # Señal de test OK para el modo auto
                        self.sig_test_finalizado.emit(True)

                        if DEBUGG:
                            QMessageBox.information(
                                self.ui, 
                                "Resultado Exitoso", 
                                f"Transistor en buen estado\n\nGanancia medida (HFE): {valor_HFE}"
                            )
                    else:
                        self.sig_test_finalizado.emit(False)

                        if DEBUGG:
                            # Mensaje de error detallado
                            QMessageBox.critical(
                                self.ui, 
                                "Falla en el componente", 
                                f"PRUEBA FALLIDA (HFE = {valor_HFE})\n\n"
                                "Posibles causas:\n"
                                "1. El transistor está dañado (Abierto/Corto).\n"
                                "2. Conexión incorrecta o falsos contactos.\n"
                                "3. El componente no es un BJT NPN compatible."
                            )
                    return # Importante: No seguir procesando para que no se guarde en el CSV
                
            except Exception as e:
                print(f"Error procesando test: {e}")

        if "# Fin" in data:
            # El Arduino terminó de enviar datos de Entrada o Salida
            self.sig_barrido_finalizado.emit()
            # No hacemos return aquí porque quizás se quiera guardar esa línea en el log

        # Guardar en archivo si se seleccionó carpeta
        if self.proyect_path:
            if self.data_send == 'LEER_SALIDA':
                file_path = os.path.join(self.proyect_path, "Salida/salida.csv")
            elif self.data_send == 'LEER_ENTRADA':
                file_path = os.path.join(self.proyect_path, "Entrada/entrada.csv")
            elif self.data_send == 'LEER_TODO':
                file_path = os.path.join(self.proyect_path, "Todo/todo.csv")
            else:
                file_path = os.path.join(self.proyect_path, "log.csv")
            try:
                modo_escritura = 'a'
                if "# Barrido" in data: 
                    modo_escritura = 'w'
                with open(file_path, modo_escritura, encoding="utf-8") as f:
                    f.write((data + '\n'))
            except Exception as e:
                if DEBUGG:
                    self.ui.receive_text.append(f"[Error al guardar archivo]: {e}")

    def closeEvent(self, event):
        if self.reader_thread:
            self.reader_thread.stop()
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        event.accept()

    def leer_condiciones(self, type:str = "salida"):
        '''
        Devuelve (Temperatura, Humedad) de los datos cargados.
        '''
        df = None
        if type == 'salida':
            df = self.exit_df
        else:
            df = self.entry_df
            
        if df is not None:
            # Buscamos columnas que contengan "Temperatura" y "Humedad"
            col_temp = next((c for c in df.columns if "Temperatura" in c), None)
            col_hum = next((c for c in df.columns if "Humedad" in c), None)
            
            t_val = 0.0
            h_val = 0.0
            
            if col_temp and col_hum:
                # Retornamos el promedio de las lecturas (ignoran los ERROR si se filtraron antes)
                t_series = pd.to_numeric(df[col_temp], errors='coerce')
                h_series = pd.to_numeric(df[col_hum], errors='coerce')
                
                t_val = t_series.mean()
                h_val = h_series.mean()
                
            return t_val, h_val
        return 0.0, 0.0

    def cargar_csv(self, path, type:str = "salida"):
        """
        Carga el CSV en un DataFrame, detectando la fila de encabezados.
        type: 'salida' , 'entrada' , 'todo'
        """
        # 1. Leer todas las lineas para buscar el encabezado
        with open(path, "r", encoding="utf-8") as f:
            lineas = f.readlines()
        
        header_line = 0
        # 2. Buscamos la linea que tenga los encabezados correctos
        for i, linea in enumerate(lineas):
            # Buscamos coincidencias con lo que manda el ESP32 ahora
            if "Indice" in linea and "cuentas" in linea:
                header_line = i
                break

        # 3. Cargar el CSV ignorando las lineas de comentarios (#) automáticamente
        # Pandas es inteligente: si le decimos comment='#', ignora las lineas metadata de arriba
        # pero necesitamos asegurarnos de leer la fila de headers correcta.
        
        try:
            # header=0 relativo a los datos leidos despues de saltar filas metadata si fuera necesario
            # Pero como usas skiprows, vamos directo a la linea.
            df = pd.read_csv(path, skiprows=header_line, comment='#')
            
            # Limpieza básica: Eliminar columnas vacias o filas de error si las hubiera
            df = df.dropna(how='all') 
            
            if type == 'salida':
                self.exit_df = df
            elif type == 'entrada':
                self.entry_df = df
            elif type == 'todo':
                self.all_df = df
                
        except Exception as e:
            QMessageBox.critical(self, "Error de Carga", f"No se pudo leer el CSV:\n{e}")

    def cargar_exit_df(self):
        self.exit_path = os.path.join(self.proyect_path, "Salida")
        if os.path.exists(self.exit_path):
            csv_path = os.path.join(self.exit_path, "salida.csv")
            
            # 1. Cargar datos
            try:
                self.cargar_csv(csv_path, 'salida')
                if self.exit_df is None or self.exit_df.empty:
                    QMessageBox.warning(self, "Datos", "No hay datos cargados.")
                    return FAIL
                return OK
            except:
                raise FileNotFoundError(f"La ruta: {csv_path} no existe o no se puede leer.")

        return OK

    def cargar_entry_df(self):
        self.entry_path = os.path.join(self.proyect_path, "Entrada")
        if os.path.exists(self.entry_path):
            csv_path = os.path.join(self.entry_path, "entrada.csv")
            
            # 1. Cargar datos
            try:
                self.cargar_csv(csv_path, 'entrada')
                if self.entry_df is None or self.entry_df.empty:
                    QMessageBox.warning(self, "Datos", "No hay datos cargados.")
                    return FAIL
                return OK
            except:
                raise FileNotFoundError(f"La ruta: {csv_path} no existe o no se puede leer.")

        return OK

    def generate_report(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 1. Definir la ruta del script
        script_path = os.path.join(base_dir, "my_report.py")
        
        # 2. Obtener el modelo del input
        modelo = self.ui.model_input.text().strip()
        if not modelo: 
            modelo = "Generico"

        cant_muestras = str(self.ui.spin_muestras.value()) 

        if not os.path.exists(script_path):
            QMessageBox.critical(self, "Error", f"No se encuentra el script en:\n{script_path}")
            return
        
        # 3. Crear y mostrar diálogo de espera (Modal)
        waiting = WaitingDialog(self)
        waiting.show()
        # Forzar a que la UI se pinte antes de bloquear el hilo
        QApplication.processEvents()

        try:
             # 4. EJECUCIÓN ÚNICA: Pasamos 'modelo' en la lista de argumentos
            t_val, h_val = self.leer_condiciones('salida')
            my_report.generar_pdf_final(temperatura=t_val, proyect_path=self.proyect_path, humedad=h_val, Muestras=cant_muestras, modelo_transistor=modelo)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Fallo al generar informe:\n{e}")
        finally:
            # 5. Cerrar diálogo al finalizar
            waiting.close()

    def full_generate_report(self):
        """
        Inicio de la Secuencia Automática.
        """

        # Chequeo de seguridad
        if not self.serial_port or not self.serial_port.is_open:
            QMessageBox.warning(self, "Error", "Conecte el puerto primero.")
            return

        # Bloquear UI para que el usuario no toque nada mientras trabaja
        self.ui.full_report_button.setEnabled(False)
        self.ui.full_report_button.setText("Ejecutando Test...")
        self.ui.status_label.setText("Estado: Iniciando secuencia...")

        # Asegurar configuración (Muestras/Curvas)
        self.send_configuration()
        QThread.msleep(1)
        
        # --- INICIO DE LA MÁQUINA DE ESTADOS ---
        self.current_state = 1  # Pasamos a Estado 1 (Testing)
        self.realizar_test()    # Disparamos la acción
        
        # Ahora esperamos a que suene la señal 'sig_test_finalizado'.

    
    def on_test_finished(self, paso_ok):
        """
        Se ejecuta cuando llega la señal sig_test_finalizado(bool)
        """
        # Verificamos que estemos en el paso correcto de la secuencia
        if self.current_state != 1: 
            return

        if paso_ok:
            # --- TRANSICIÓN: DEL TEST (1) A ENTRADA (2) ---
            self.current_state = 2
            self.ui.full_report_button.setText("Midiendo Entrada...")
            self.ui.status_label.setText("Estado: Midiendo Curva de Entrada...")
            
            # Disparar siguiente acción (usamos tu función existente)
            self.send_data("LEER_ENTRADA") 
            
        else:
            # --- FALLO: ABORTAR ---
            mensaje_error = (
                "El componente no pasó el TEST.\n\n"
                "Posibles causas:\n"
                "1. El transistor está dañado (Abierto/Corto).\n"
                "2. Conexión incorrecta o falsos contactos.\n"
                "3. El componente no es un BJT NPN compatible."
            )
            self.abortar_secuencia(mensaje_error)

    def on_sweep_finished(self):
        """
        Se ejecuta cuando llega la señal sig_barrido_finalizado()
        """
        # CASO A: Terminó el barrido de ENTRADA (Estado 2)
        if self.current_state == 2:
            # --- TRANSICIÓN: DE ENTRADA (2) A SALIDA (3) ---
            self.current_state = 3
            self.ui.full_report_button.setText("Midiendo Salida...")
            self.ui.status_label.setText("Estado: Midiendo Curva de Salida...")
            
            # Configurar variable de envío
            self.data_send = "LEER_SALIDA"
            
            # Disparar siguiente acción
            self.send_data()

        # CASO B: Terminó el barrido de SALIDA (Estado 3)
        elif self.current_state == 3:
            # --- FIN: DE SALIDA (3) A REPORTE ---
            self.ui.full_report_button.setText("Generando PDF...")
            self.ui.status_label.setText("Estado: Procesando datos...")
            
            # Procesar y Generar
            try:
                self.procesar_y_graficar_entrada()
                self.procesar_y_graficar_salida()
                self.generate_report() # Tu script externo
                
                # Restaurar todo
                self.ui.status_label.setText("Estado: ¡Informe Terminado!")
                QMessageBox.information(self, "Éxito", "Secuencia completada. Informe generado.")
                
            except Exception as e:
                self.abortar_secuencia(f"Error al generar informe: {e}")
            
            finally:
                self.reset_ui_state()

    def abortar_secuencia(self, mensaje):
        """
        Función auxiliar para cancelar todo si algo sale mal
        """
        QMessageBox.critical(self, "Error", mensaje)
        self.ui.status_label.setText("Estado: Error en secuencia.")
        self.reset_ui_state()

    def reset_ui_state(self):
        """Devuelve el botón a la normalidad"""
        self.current_state = 0
        self.ui.full_report_button.setEnabled(True)
        self.ui.full_report_button.setText("Generar Informe Completo")


    def send_configuration(self):
        """
        Lee los valores de los SpinBox y los envía al ESP32 con el formato: "MUESTRAS{X}" y "CURVAS{Y}".
        """
        if self.serial_port and self.serial_port.is_open:
            # Obtener valores de la interfaz
            n_muestras = self.ui.spin_muestras.value()
            n_curvas = self.ui.spin_curvas.value()
            
            # Actualizar también las variables globales para calculos
            global Muestras, Curvas
            Muestras = n_muestras
            Curvas = n_curvas
            
            # Actualizar el calculador de incertidumbre con las nuevas muestras (N)
            self.incertidumbre.n = n_muestras 

            try:
                # Enviar comandos
                # MUESTRAS
                cmd_muestras = f"MUESTRAS{n_muestras}"
                self.serial_port.write((cmd_muestras + '\n').encode())
                
                # Pequeña pausa de seguridad (opcional, pero recomendada en serial)
                QThread.msleep(50) 
                
                # CURVAS
                cmd_curvas = f"CURVAS{n_curvas}"
                self.serial_port.write((cmd_curvas + '\n').encode())
                
                if DEBUGG:
                    self.ui.receive_text.append(f"--- CONFIGURACIÓN ENVIADA ---\n> {cmd_muestras}\n> {cmd_curvas}")
                
                # QMessageBox.information(self, "Éxito", f"Configurado:\n- Muestras: {n_muestras}\n- Curvas: {n_curvas}")

            except Exception as e:
                QMessageBox.critical(self, "Error Serial", f"Fallo al enviar configuración:\n{e}")
        else:
            QMessageBox.warning(self, "Puerto cerrado", "Primero conecta el ESP32.")

    def update_estimation(self):
        """
        Calcula el tiempo estimado con Alta Precisión basado en datos del 10/02/2026.
        
        1. Salida: T = Curvas * (448ms + (276ms * Muestras))
        2. Entrada: T = 2200ms + (392ms * Muestras)
        """
        # Obtener valores de la interfaz
        n_muestras = self.ui.spin_muestras.value()
        n_curvas = self.ui.spin_curvas.value()
        modo = self.ui.send_combo.currentText()
        
        total_ms = 0.0
        
        # --- CONSTANTES "MEDIDAS" ---
        # SALIDA
        OUT_OVERHEAD_PER_CURVE = 448.0  # Tiempo muerto por curva (setup DAC, delay)
        OUT_TIME_PER_SAMPLE    = 276.0  # Tiempo de proceso por cada muestra de promedio
        
        # ENTRADA
        IN_BASE_TIME           = 2200.0 # Tiempo fijo (búsqueda de límites + overhead)
        IN_TIME_PER_SAMPLE     = 392.0  # Tiempo extra por cada muestra de promedio

        # --- CÁLCULO ---

        if not DEBUGG:
            modo = "LEER_TODO"

        if modo == "LEER_SALIDA":
            # Formula: Curvas * (Fijo + Variable*Muestras)
            time_per_curve = OUT_OVERHEAD_PER_CURVE + (OUT_TIME_PER_SAMPLE * n_muestras)
            total_ms = n_curvas * time_per_curve
            
        elif modo == "LEER_ENTRADA":
            # Formula: Base + Variable*Muestras
            total_ms = IN_BASE_TIME + (IN_TIME_PER_SAMPLE * n_muestras)
            
        elif modo == "LEER_TODO":
            # Suma de ambos modelos
            t_salida = n_curvas * (OUT_OVERHEAD_PER_CURVE + (OUT_TIME_PER_SAMPLE * n_muestras))
            t_entrada = IN_BASE_TIME + (IN_TIME_PER_SAMPLE * n_muestras)
            total_ms = t_salida + t_entrada

        # --- FORMATO ---
        texto_tiempo = ""
        if total_ms < 1000:
            texto_tiempo = f"{int(total_ms)} ms"
        elif total_ms < 60000:
            segundos = total_ms / 1000.0
            texto_tiempo = f"{segundos:.1f} s"
        else:
            minutos = total_ms / 60000.0
            texto_tiempo = f"{minutos:.1f} min"
        
        self.ui.time_label.setText(f'Tiempo estimado: ~{texto_tiempo}')


    # ------------------------------------------------------------------------
    #   GETTERS
    # ------------------------------------------------------------------------

    def get_output_data(self):
        """
        Carga 'Salida/salida.csv', calcula valores físicos con sus incertidumbres.

        Retorna: DataFrame con columnas:
            [Indice, Vce, u_Vce, IC, u_Ic, IB, u_Ib]
        """
        if self.cargar_exit_df() == FAIL:
            return None
        
        # Limpieza
        df = self.exit_df.copy()
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna()

        # Cálculos físicos e incertidumbre (VCE, IC, IB)
        
        
        # VCE
        V13_cuentas = df['V13[cuentas]']
        V13_std = df['V13_s[cuentas]']
        VCE_med_V = self.incertidumbre.CadsToVads(V13_cuentas)
        u_VCE_V = self.incertidumbre.uC_ads_voltage(V13_cuentas, V13_std)
        U_VCE_V = self.incertidumbre.Expansion_TCL_95(u_VCE_V)

        # IC
        I3_cuentas = df['I3[cuentas]']
        I3_std = df['I3_s[cuentas]']
        Ic_med_mA = self.incertidumbre.CinaToAina(I3_cuentas) * 1000.0
        u_IC_A = self.incertidumbre.uC_ina_current(I3_cuentas, I3_std)
        U_IC_mA = self.incertidumbre.Expansion_TCL_95(u_IC_A) * 1000.0

        # IB
        IB_uA, u_IB_uA = self.incertidumbre.calculos_Ib_ucurrent(
            df['V10[cuentas]'], df['V10_s[cuentas]'], 
            df['V12[cuentas]'], df['V12_s[cuentas]']
        )
        U_IB_uA = self.incertidumbre.Expansion_TCL_95(u_IB_uA)

        # Armado del "DataFrame Físico"
        df_phys = pd.DataFrame()

        df_phys['Indice'] = df['Indice']
        df_phys['VCE_V'] = VCE_med_V
        df_phys['U_VCE_V'] = U_VCE_V
        df_phys['IC_mA'] = Ic_med_mA
        df_phys['U_IC_mA'] = U_IC_mA
        df_phys['IB_uA'] = IB_uA
        df_phys['U_IB_uA'] = U_IB_uA

        # Opcional: Guardar CSV físico intermedio
        # df_phys.to_csv(os.path.join(self.exit_path, "salida_fisica_procesada.csv"), index=False)
        
        return df_phys

    def get_input_data(self):
        """
        Carga 'Entrada/entrada.csv', calcula valores físicos e incertidumbres.
        Retorna: DataFrame con VBE, IC, IB y sus incertidumbres.
        """
        if self.cargar_entry_df() == FAIL:
            return None
        
        # Limpieza
        df = self.entry_df.copy()
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna()

        # VBE
        VCE_cuentas = df['V13[cuentas]']
        VCE_std = df['V13_s[cuentas]']
        VCE_med_V = self.incertidumbre.CadsToVads(VCE_cuentas)
        u_VCE_V = self.incertidumbre.uC_ads_voltage(VCE_cuentas, VCE_std)
        U_VCE_V = self.incertidumbre.Expansion_TCL_95(u_VCE_V)

        # VBE
        VBE_cuentas = df['V12[cuentas]']
        VBE_std = df['V12_s[cuentas]']
        VBE_med_V = self.incertidumbre.CadsToVads(VBE_cuentas)
        u_VBE_V = self.incertidumbre.uC_ads_voltage(VBE_cuentas, VBE_std)
        U_VBE_V = self.incertidumbre.Expansion_TCL_95(u_VBE_V)

        # IB
        IB_uA_med, u_IB_uA = self.incertidumbre.calculos_Ib_ucurrent(
            df['V10[cuentas]'], df['V10_s[cuentas]'], 
            df['V12[cuentas]'], df['V12_s[cuentas]']
        )
        U_IB_uA = self.incertidumbre.Expansion_TCL_95(u_IB_uA)

        # IC
        IC_mA_med = self.incertidumbre.CinaToAina(df['I3[cuentas]']) * 1000.0
        u_IC_mA = self.incertidumbre.uC_ina_current(df['I3[cuentas]'], df['I3_s[cuentas]']) * 1000.0
        U_IC_mA = self.incertidumbre.Expansion_TCL_95(u_IC_mA)

        # HFE
        HFE_med = self.incertidumbre.HFE(IC_mA_med, IB_uA_med)
        u_HFE = self.incertidumbre.uC_HFE(IC_mA_med, u_IC_mA, IB_uA_med, u_IB_uA)
        U_HFE = self.incertidumbre.Expansion_TCL_95(u_HFE)
                
        # Armado del "DataFrame Físico"
        df_phys = pd.DataFrame()

        df_phys['Indice'] = df['Indice']
        df_phys['VCE_V'] = VCE_med_V
        df_phys['U_VCE_V'] = U_VCE_V
        df_phys['VBE_V'] = VBE_med_V
        df_phys['U_VBE_V'] = U_VBE_V
        df_phys['IB_uA'] = IB_uA_med
        df_phys['U_IB_uA'] = U_IB_uA
        df_phys['IC_mA'] = IC_mA_med
        df_phys['U_IC_mA'] = U_IC_mA
        df_phys['HFE'] = HFE_med
        df_phys['U_HFE'] = U_HFE

        # Opcional: Guardar CSV físico intermedio
        # df_phys.to_csv(os.path.join(self.exit_path, "entrada_fisica_procesada.csv"), index=False)

        return df_phys
    
    # ------------------------------------------------------------------------
    #   PLOTTER
    # ------------------------------------------------------------------------
    
    def plot_generico(self, df, x_col, y_col, dx_col, dy_col, 
                      xlabel, ylabel, title, filename, 
                      xscale='linear', yscale='linear', 
                      group_col=None,
                      label_col=None, label_err_col=None, label_method='last'):
        """
        Graficador universal con incertidumbre expandida.
        
        Args:
            df: DataFrame con los datos FÍSICOS (Salida de los getters).
            x_col, y_col: Nombres de las columnas de datos (ej: 'Vce', 'IC').
            dx_col, dy_col: Nombres de las columnas de incertidumbre (ej: 'U_Vce').
            xlabel, ylabel, title: Textos para el gráfico.
            filename: Nombre del archivo a guardar (ej: 'Entrada/ganancia.png').
            xscale, yscale: 'linear' o 'log'.
            group_col: (Opcional) Columna para separar curvas (ej: 'Indice').
            label_col: (Opcional) Columna para usar en la leyenda (ej: 'IB').
            label_err_col: (Opcional) Columna de incertidumbre para el dato de leyenda. Si es None, busca automáticamente "U_{label_col}".
            label_method: Cómo resumir el dato de la leyenda. Opciones: 'mean' (Promedio de todo), 'last' (Último), 'first' (Primero).
        """

        # Limpieza
        if df is None or df.empty:
            return

        # Definicion del plot
        plt.figure(figsize=(10, 6))
        ax = plt.gca()

        # Agrupamiento (Salida o Entrada)
        if group_col and group_col in df.columns:
            grupos = df.groupby(group_col)
        else:
            # Si no hay grupos, hacemos un grupo falso con todo el DF
            grupos = [("Unica", df)]

        # Iteramos sobre las curvas (puede ser 1 o muchas)
        for nombre_grupo, grupo in grupos:
            # Extraer datos seguros
            x = grupo[x_col].values
            y = grupo[y_col].values
            dx = grupo[dx_col].values
            dy = grupo[dy_col].values
            
            # Generar leyenda
            etiqueta = str(nombre_grupo)

            # Solo procesamos etiqueta personalizada si nos pasaron una columna
            if label_col and label_col in grupo.columns:

                # Obtener series de datos y de incertidumbre
                serie_dato = grupo[label_col]
                nombre_col_u = label_err_col

                nombre_col_u = label_err_col if label_err_col else f"U_{label_col}"
                
                # Si existe la usamos, si no, asumimos 0
                if nombre_col_u in grupo.columns:
                    serie_u = grupo[nombre_col_u]
                else:
                    serie_u = pd.Series(0, index=grupo.index)

                # 2. Aplicar el método de selección (mean, last, first)
                val_disp = 0.0
                u_disp = 0.0

                try:
                    if label_method == 'mean':
                        val_disp = serie_dato.mean()
                        u_disp = serie_u.mean()     # Promedio general de la incertidumbre
                    elif label_method == 'last':
                        val_disp = serie_dato.iloc[-1]
                        u_disp = serie_u.iloc[-1]   # Incertidumbre del último punto
                    elif label_method == 'first':
                        val_disp = serie_dato.iloc[0]
                        u_disp = serie_u.iloc[0]    # Incertidumbre del primer punto
                    else:   # Si escribieron mal el método
                        val_disp = serie_dato.mean()
                        u_disp = serie_u.mean()
                except Exception:
                    val_disp = 0
                    u_disp = 0
            
                # Formateo
                etiqueta = f"{label_col} = {val_disp:.3f} ± {u_disp:.3f}"

            # Graficar línea
            p, = plt.plot(x, y, 'o-', markersize=3, label=etiqueta)
            color = p.get_color()

            # Graficar rectángulos de incertidumbre expandida
            for val_x, val_y, val_dx, val_dy in zip(x, y, dx, dy):
                rect = Rectangle(
                    (val_x - val_dx, val_y - val_dy), 
                    width=2*val_dx, height=2*val_dy,
                    linewidth=0, facecolor=color, alpha=0.3
                )
                ax.add_patch(rect)

        # Configuración final
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title)
        plt.xscale(xscale)
        plt.yscale(yscale)
        plt.grid(True, which='both', linestyle='--', alpha=0.7)
        
        # Leyenda inteligente: Se pone si hay muchas curvas, opcional.
        if group_col: 
            plt.legend(fontsize='small')
        
        # Zoom inteligent: Para escalas logarítmicas (evita ceros)
        if yscale == 'log':
            valid_y = df[df[y_col] > 0][y_col]
            if not valid_y.empty:
                plt.ylim(bottom=valid_y.min() * 0.9)

        # Guardar
        full_path = os.path.join(self.proyect_path, filename)
        plt.savefig(full_path, dpi=300)
        plt.close()
        
        if DEBUGG: print(f"Generado: {filename}")

    # ------------------------------------------------------------------------
    #   FUNCIONES GENERALES DE ENTRADA Y SALIDA (ya se agrupa todo)
    # ------------------------------------------------------------------------

    def procesar_y_graficar_entrada(self):
        """
        Generación de gráficos del barrido de ENTRADA.
        """
        # Obtener datos físicos
        df_in = self.get_input_data()
        if df_in is None: return

        # Gráfico 1: IB vs VBE (Lineal)
        self.plot_generico(
            df=df_in,
            x_col='VBE_V',   dx_col='U_VBE_V',
            y_col='IB_uA', dy_col='U_IB_uA',
            xlabel='VBE [V]', ylabel='IB [uA]',
            title='Característica de Entrada',
            filename='Entrada/curva_IB_vs_VBE.png',
            group_col='Indice',         # Separa las curvas por el índice del barrido
            label_col='VCE_V',          # Usa la columna 'VCE_V' para poner "VCE_V = XX V" en la leyenda
            label_err_col='U_VCE_V'     # Usa la columna 'U_VCE_V' para poner "±XX V" en la leyenda
        )

        # Gráfico 2: IC vs VBE (Lineal)
        self.plot_generico(
            df=df_in,
            x_col='VBE_V',   dx_col='U_VBE_V',
            y_col='IC_mA', dy_col='U_IC_mA',
            xlabel='VBE [V]', ylabel='IC [mA]',
            title='Característica de Entrada',
            filename='Entrada/curva_IC_vs_VBE.png',
            group_col='Indice',         # Separa las curvas por el índice del barrido
            label_col='VCE_V',          # Usa la columna 'VCE_V' para poner "VCE_V = XX V" en la leyenda
            label_err_col='U_VCE_V'     # Usa la columna 'U_VCE_V' para poner "±XX V" en la leyenda
        )

        # Gráfico 3: HFE vs IC (Semi-Log X)
        # Filtramos las filas donde HFE sea válido (no NaN) y mayor que 0
        df_hfe = df_in.dropna(subset=['HFE']).copy()
        # Segundo filtro grafico
        # Debajo de eso, la incertidumbre domina (si limitamos por corriente es algo tipico de los fabricantes (pero es mejor asi))
        df_hfe = df_hfe[df_hfe['HFE'] >= (2 * df_hfe['U_HFE'])]
        
        self.plot_generico(
            df=df_hfe,
            x_col='IC_mA', dx_col='U_IC_mA',
            y_col='HFE',   dy_col='U_HFE',
            xlabel='IC [mA]', ylabel='HFE [-]',
            title='HFE',
            filename='Entrada/curva_HFE_vs_IC.png',
            group_col='Indice',         # Separa las curvas por el índice del barrido
            label_col='VCE_V',          # Usa la columna 'VCE_V' para poner "VCE_V = XX V" en la leyenda
            label_err_col='U_VCE_V',    # Usa la columna 'U_VCE_V' para poner "±XX V" en la leyenda
            xscale='log',               # Escala logarítmica
            yscale='log'                # Escala logarítmica
        )

        # Gráfico 4: VBE[V] vs IC[mA]
        self.plot_generico(
            df=df_in,
            x_col='IC_mA', dx_col='U_IC_mA',
            y_col='VBE_V', dy_col='U_VBE_V',
            xlabel='IC [mA]', ylabel='VBE [V]',
            title='VBE[V] vs IC[mA]',
            filename='Entrada/curva_VBE_vs_IC.png',
            group_col='Indice',         # Separa las curvas por el índice del barrido
            label_col='VCE_V',          # Usa la columna 'VCE_V' para poner "VCE_V = XX V" en la leyenda
            label_err_col='U_VCE_V',    # Usa la columna 'U_VCE_V' para poner "±XX V" en la leyenda
            xscale='log'
        )
        
        # Guardar CSV
        df_in.to_csv(os.path.join(self.proyect_path, "Entrada/entrada_fisica.csv"), index=False)

    def procesar_y_graficar_salida(self):
        """
        Generación de gráficos del barrido de SALIDA.
        """
        if DEBUGG: print("Procesando Salida...")
        
        # Obtener datos físicos
        df_out = self.get_output_data()
        if df_out is None: return

        # Generar plots usando plot_generico
        save_dir = "Salida"
        
        # Gráfico 1: IC vs VCE
        self.plot_generico(
            df=df_out,
            x_col='VCE_V',   dx_col='U_VCE_V',
            y_col='IC_mA',    dy_col='U_IC_mA',
            xlabel='VCE [V]', ylabel='IC [mA]',
            title='Curvas de Salida (IC vs VCE)',
            filename='Salida/curva_IC_vs_VCE.png',
            group_col='Indice',     # Separa las curvas por el índice del barrido
            label_col='IB_uA',      # Usa la columna 'IB_uA' para poner "IB = XX uA" en la leyenda
            label_err_col='U_IB_uA' # Usa la columna 'U_IB_uA' para poner "±XX uA" en la leyenda
        )

        # Gráfico 2: IB vs VCE
        self.plot_generico(
            df=df_out,
            x_col='IB_uA',   dx_col='U_IB_uA',
            y_col='VCE_V',    dy_col='U_VCE_V',
            xlabel='IB [uA]', ylabel='VCE [V]',
            title='Curvas de Salida (IB vs VCE)',
            filename='Salida/curva_IB_vs_VCE.png',
            xscale='log',
            group_col='Indice',     # Separa las curvas por el índice del barrido
            label_col='IC_mA',      # Usa la columna 'IC_mA' para poner "IC = XX mA" en la leyenda
            label_err_col='U_IC_mA' # Usa la columna 'U_IC_mA' para poner "±XX mA" en la leyenda
        )

        # Guardar CSV Físico final
        # Este archivo es el que va a leer luego tu script 'my_report.py'
        path_csv = os.path.join(self.proyect_path, "Salida", "salida_fisica.csv")
        df_out.to_csv(path_csv, index=False)
        
        if DEBUGG: print(f"Salida procesada. CSV guardado en: {path_csv}")

    def realizar_test(self):
        """Envía el comando de test al Arduino"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.write(b"TEST\n")
            if DEBUGG: print("Enviado: TEST")
        else:
            QMessageBox.warning(self, "Error", "Conecte el puerto serie primero.")


'''
#######################################################################################

                                    CLASES

#######################################################################################
'''

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if DARK_MODE:
        apply_dark_theme(app)
    window = TrazadorApp()
    window.show()
    sys.exit(app.exec_())