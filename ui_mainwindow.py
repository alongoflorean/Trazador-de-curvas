'''
#######################################################################################

                                    IMPORTS

#######################################################################################
'''

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox,
    QPushButton, QTextEdit, QHBoxLayout,QLineEdit,QDialog
)
# Para el "tema oscuro"
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QFileDialog, QMessageBox,
    QSpinBox, QGroupBox, QSpacerItem, QSizePolicy
)

Muestras = 10
Curvas = 5

'''
#######################################################################################

                                    TEMA OSCURO

#######################################################################################
'''
def apply_dark_theme(app):
    app.setStyle("Fusion")
    palette = QPalette()

    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)

    app.setPalette(palette)
    app.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }")




'''
#######################################################################################

                                    VENTANA PRINCIPAL 

#######################################################################################
'''


class Ui_Form:
    def setupUi(self, Form, debugg = False):
        Form.setWindowTitle("Selector de Puerto COM")
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Seleccione un puerto COM:"))

        # Layout horizontal para combo + botón refresh
        port_layout = QHBoxLayout()
        self.port_combo = QComboBox()
        port_layout.addWidget(self.port_combo)

        self.refresh_button = QPushButton("↻")  # Botón de refresh
        #self.refresh_button.setToolTip("Actualizar lista de puertos")
        port_layout.addWidget(self.refresh_button)

        layout.addLayout(port_layout)

        self.open_button = QPushButton("Abrir Puerto")
        layout.addWidget(self.open_button)

        self.com_status_label = QLabel("Puerto Desconectado")
        self.com_status_label.setStyleSheet("color: red;")
        layout.addWidget(self.com_status_label)

        self.status_label = QLabel("No se ha seleccionado carpeta de proyecto")
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label)

        # Botón para seleccionar carpeta
        self.select_folder_button = QPushButton("Seleccionar carpeta de proyecto")
        layout.addWidget(self.select_folder_button)

        # Enviar datos
        if debugg:
            layout.addWidget(QLabel("Enviar trama:"))

        h_layout = QHBoxLayout()
        self.send_combo = QComboBox()
        self.send_combo.setEditable(False)
        self.send_combo.addItems(["LEER_SALIDA", "LEER_ENTRADA"])
        h_layout.addWidget(self.send_combo)

        self.send_button = QPushButton("Medir")
        h_layout.addWidget(self.send_button)
        layout.addLayout(h_layout)

        self.btn_test = QPushButton("Test")
        self.btn_test.setStyleSheet("background-color: #8e44ad; color: white; font-weight: bold;") # Violeta para distinguir
        self.btn_test.setToolTip("Verificar estado del transistor (HFE >= 50)")
        h_layout.addWidget(self.btn_test) # Mismo layout horizontal

        if not debugg:
            self.btn_test.setVisible(False)  # Existe, pero es invisible
            self.send_combo.setVisible(False)
            self.send_button.setVisible(False)

        self.config_group = QGroupBox("Configuración Inicial")
        self.config_layout = QHBoxLayout()
        
        # Selector de Muestras
        self.label_muestras = QLabel("Muestras:")
        self.spin_muestras = QSpinBox()
        self.spin_muestras.setRange(1, 200)
        self.spin_muestras.setValue(Muestras) 
        
        # Selector de Curvas
        self.label_curvas = QLabel("Curvas:")
        self.spin_curvas = QSpinBox()
        self.spin_curvas.setRange(1, 15)
        self.spin_curvas.setValue(Curvas)

        # Botón de Configurar
        self.btn_config = QPushButton("Inicializar ESP32")
        self.btn_config.setStyleSheet("background-color: #d35400; color: white; font-weight: bold;")

        if not debugg:
            self.btn_config.setVisible(False)

        self.time_label = QLabel("Tiempo estimado: -")
        self.time_label.setStyleSheet("color: #2a82da; font-weight: bold; font-size: 12px;")
        self.time_label.setAlignment(Qt.AlignCenter)

        # Agregar todo al layout horizontal del grupo
        self.config_layout.addWidget(self.label_muestras)
        self.config_layout.addWidget(self.spin_muestras)
        self.config_layout.addSpacing(20)
        self.config_layout.addWidget(self.label_curvas)
        self.config_layout.addWidget(self.spin_curvas)
        self.config_layout.addSpacing(20)
        self.config_layout.addWidget(self.btn_config)
        
        # REEMPLAZO DE LA ESTRUCTURA DEL LAYOUT DEL GRUPO:
        self.group_main_layout = QVBoxLayout() # Layout vertical principal del grupo
        self.controls_layout = QHBoxLayout()   # Layout horizontal para los botones (el que tenías)
        
        # Agregamos los controles al horizontal
        self.controls_layout.addWidget(self.label_muestras)
        self.controls_layout.addWidget(self.spin_muestras)
        self.controls_layout.addSpacing(20)
        self.controls_layout.addWidget(self.label_curvas)
        self.controls_layout.addWidget(self.spin_curvas)
        self.controls_layout.addSpacing(20)
        self.controls_layout.addWidget(self.btn_config)
        
        # Armamos el vertical
        self.group_main_layout.addLayout(self.controls_layout)
        self.group_main_layout.addWidget(self.time_label) # Tiempo abajo
        
        self.config_group.setLayout(self.group_main_layout)

        # 6. Agregarlo al layout principal
        layout.addWidget(self.config_group)

        # Recibir datos
        if debugg:
            layout.addWidget(QLabel("Datos recibidos:"))
            self.receive_text = QTextEdit()
            self.receive_text.setReadOnly(True)
            layout.addWidget(self.receive_text)

            # Botones Test Plot y otro al lado
            button_layout = QHBoxLayout()
            self.exit_plot_button = QPushButton("Plot de salida")
            button_layout.addWidget(self.exit_plot_button)

            self.entry_plot_button = QPushButton("Plot de entrada")
            button_layout.addWidget(self.entry_plot_button)

            layout.addLayout(button_layout)

            self.report_button = QPushButton("Generar Informe")
            self.report_button.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;") 
            
            model_layout = QHBoxLayout()
            model_layout.addWidget(QLabel("Modelo de Transistor:"))
            self.model_input = QLineEdit()
            self.model_input.setPlaceholderText("Ej: BC547, 2N2222...")
            self.model_input.setText("Generico NPN") # Valor por defecto
            model_layout.addWidget(self.model_input)
            
            layout.addLayout(model_layout)
            
            layout.addWidget(self.report_button)
        else:
            model_layout = QHBoxLayout()
            model_layout.addWidget(QLabel("Modelo de Transistor:"))
            self.model_input = QLineEdit()
            self.model_input.setPlaceholderText("Ej: BC547, 2N2222...")
            self.model_input.setText("Generico NPN") # Valor por defecto
            model_layout.addWidget(self.model_input)
            layout.addLayout(model_layout)

            self.full_report_button = QPushButton("Generar Informe")
            self.full_report_button.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
            # self.btn_test.setToolTip("Mensaje simple de descripcion")
            layout.addWidget(self.full_report_button)

        Form.setLayout(layout)
    

'''
#######################################################################################

               VENTANA INICIAL QUE OBLIGA A SELECCIONAR CARPETA DE PROYECTO 

#######################################################################################
'''


class FolderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar o crear carpeta de proyecto")

        layout = QVBoxLayout()

        # Opción 1: crear carpeta nueva
        layout.addWidget(QLabel("Ingrese el nombre de la carpeta nueva:"))
        self.folder_name_edit = QLineEdit()
        layout.addWidget(self.folder_name_edit)

        # Opción 2: elegir carpeta existente
        self.select_button = QPushButton("Elegir carpeta existente")
        layout.addWidget(self.select_button)

        self.selected_path_label = QLabel("Ninguna carpeta seleccionada")
        layout.addWidget(self.selected_path_label)

        # Botones aceptar / cancelar
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Aceptar")
        #self.cancel_button = QPushButton("Cancelar")
        button_layout.addWidget(self.ok_button)
        #button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Conexiones
        self.select_button.clicked.connect(self.choose_existing_folder)
        self.ok_button.clicked.connect(self.accept)
        #self.cancel_button.clicked.connect(self.reject)

        # Variables internas
        self.selected_path = None

    def choose_existing_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta existente")
        if folder:
            self.selected_path = folder
            self.selected_path_label.setText(f"Carpeta seleccionada: {folder}")

    def accept(self):
        """Validación: debe elegir una opción (nueva o existente)"""
        name = self.folder_name_edit.text().strip()
        if not name and not self.selected_path:
            QMessageBox.warning(self, "Atención", "Debe ingresar un nombre de carpeta o seleccionar una existente.")
            return
        if name and self.selected_path:
            QMessageBox.warning(self, "Atención", "Debe elegir solo una opción: nombre nuevo o carpeta existente.")
            return
        super().accept()

    def get_result(self):
        """Devuelve el nombre de carpeta o la ruta existente"""
        name = self.folder_name_edit.text().strip()
        if name:
            return name
        return self.selected_path
    
'''
Ventana de espera al generar informe
'''
class WaitingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Procesando")
        self.setFixedSize(250, 100)
        # Quitar el botón de cerrar para obligar a esperar
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
        layout = QVBoxLayout()
        self.label = QLabel("Generando informe...\nPor favor, espere.")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        self.setLayout(layout)