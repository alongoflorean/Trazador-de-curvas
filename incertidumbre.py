#IMPORTS
import numpy as np
from mainwindow import Muestras
### Variables globales para incertidumbre

a_rectangular = np.sqrt(3)

ERROR_ADS_LSB = 3.0         # ±3LSB
ERROR_ADC_INA_REL = 1/100   # ±1%

# La idea es que se le pasan los datos como "cuentas" y devuelva todo en "tensiones" y "corrientes" (depende el caso)
class UncertaintyCalculator:
    def __init__(self, v_ref_ads = 4.096, v_ref_ina = 10e-6*(2**12), ads_bits = 16, ina_bits = 12, r_shunt_b = 1000.0, R_shunt_ina = 1, err_Rshunt_ina = 0.01, err_Rshunt_b = 0.01, n_samples = Muestras):
        """
        Inicializa el calculador con los parámetros del hardware.

        Args:
            v_ref_ads (float): Tensión de referencia del ADS1115 en Volts (es 4.096V para GAIN_ONE).
            v_ref_ina (float): Tensión de referencia del INA219 en Volts (es 0.04096V).
            ads_bits (int): Resolución del ADC del ADS1115 (16 bits).
            ina_bits (int): Resolución del ADC del INA219 (12 bits).
            R_shunt_ina (float): Valor de la resistencia de shunt del modulo INA219 en Ohms.
            r_shunt_b (float): Valor de la resistencia de shunt de base en Ohms.
            err_Rshunt_ina (float): Tolerancia de la resistencia (ej. 0.01 para 1%).
            err_Rshunt_b (float): Tolerancia de la resistencia (ej. 0.01 para 1%).
            n_samples (int): Número de muestras tomadas para el promedio (Paper dice 10).
        """
        # Cálculo del valor de 1LSB para la tension y para la corriente
        # ADS1115 en modo single-ended usa 15 bits para el rango positivo efectivo
        self.v_ref_ads = v_ref_ads
        self.ads_bits = ads_bits
        self.v_lsb = v_ref_ads / (2**(self.ads_bits - 1))

        # INA219 es de 12 bits
        # relacion_rshunt_nueva = 10  # 1 / 0.1
        self.a_lsb = (v_ref_ina / (2**ina_bits) ) / R_shunt_ina     # Pasos de 10uA (del datasheet)

        self.r_shunt_b = r_shunt_b
        self.err_Rshunt_ina = err_Rshunt_ina
        self.n = n_samples

        # Constantes

        self.uR_Rshunt_b = err_Rshunt_b / a_rectangular             # Incertidumbre relativa de la resistencia en la base (1%)
        self.ERROR_ADS_LSB = ERROR_ADS_LSB                          # Error de linealidad del ADS1115
        self.uR_LSB_ads_rel = ERROR_ADS_LSB / a_rectangular         # Incertidumbre relativa del xLSB del ADS1115
        self.uB_ref_ads_rel = 0.15 / (100 * a_rectangular)          # Incertidumbre relativa con 0.15% de error de la referencia del ADS1115
        self.ERROR_ADC_INA_REL = ERROR_ADC_INA_REL                  # 1% Error del INA219

        self.uB_adc_ina_rel = self.ERROR_ADC_INA_REL / a_rectangular
        self.uR_Rshunt_ina = self.err_Rshunt_ina / a_rectangular

    def safe_div(self, numerator, denominator, default=np.nan):
        """
        Divide arrays de forma segura. Si el denominador es 0, devuelve 'default' (NaN o 0).
        Funciona con Pandas Series y Numpy arrays.
        """
        # Convertimos a float para permitir NaN
        n = np.array(numerator, dtype=float)
        d = np.array(denominator, dtype=float)
        
        # np.divide con argumento 'where' evita el error de ejecución
        # out=full_like(...) prepara el vector resultado con el valor por defecto
        res = np.divide(n, d, out=np.full_like(n, default), where=(d!=0))
        return res

    def Expansion_TCL_95(self, valor_real): # U @95%, k=2
        '''
        Para expandir la incertidumbre con aproximacion al TCL al 95%, suponiendo gausseana
        '''
        k_exp = 1.960

        return (np.abs(valor_real * k_exp))

    def CadsToVads(self, cuentas_ads):
        return(cuentas_ads * self.v_lsb)
    
    def CinaToAina(self, cuentas_ina):
        '''Tomando las cuentas pasadas como cuentas de corriente (debido a que desde el ESP32 vienen ya con la división por Rshunt) (De todas formas es 1ohm)'''
        return(cuentas_ina * self.a_lsb)
        
    # Entran cuentas, obtengo la incertidumbre tipo A (ui) [cuentas]
    def uA(self, std_dev):
        """Calcula incertidumbre Tipo A: sigma / sqrt(n) de cualquier modulo"""
        return std_dev / np.sqrt(self.n)
        #return 0   # Para ver el impacto solo de la tipo B
    
    # Entran cuentas, obtengo la incertidumbre tipo B (uj) [cuentas]
    def uB_ads_cuentas(self, cuentas_med):  # uj(Cx)
        """
        Vads = Cnom * Vref / Ct -> Cnom = Vads * Ct / Vref
        incertidumbre_r = suma_cuadratica(Cnom_r, Vref_r)
        Cnom = c + LSB -> u_cuentas_nom = suma_cuadratica(uC_cuentas, cuentas * (LSB / raiz3))

        Calcula incertidumbre Tipo B para el ADS1115.
        Basado en el error de ±3LSB con distribución rectangular.
        """

        # No hay Cnom por estar todo enmascarado por el fabricante en los ±xLSB
        uC_LSB_ads = self.uR_LSB_ads_rel    # LSB [cuentas]

        return uC_LSB_ads

    def uB_ina_cuentas(self, cuentas_med):  # uj(Cx) [cuentas]
        """
        Calcula incertidumbre Tipo B para el INA219.
        Basado en error relativo ±1% del ADC

        uB(Cx) = sqrt(uR(ADCina)**2 * Cx_med
        """
        #uR_ADCina = self.uB_adc_ina_rel 
        #uR_Rshunt_ina = self.uR_Rshunt_ina

        #uB_cuentas = np.sqrt(uR_ADCina**2 + uR_Rshunt_ina**2) * cuentas_med
        #TODO: Modifiqué que aparezca la Rshunt en la tipo B del INA. Solo toma lo especificado por el fabricante
        return self.uB_adc_ina_rel*cuentas_med

    # Entran [cuentas] y devuelve [cuentas]
    def uC_ads_cuentas(self, cuentas_med, std_dev): # uC(Cx)
        """
        Paso intermedio antes de llegar a la uC(Vx) final

        uC(Cx) = sqrt(uA(Cx)**2 + uB(Cx)**2)

        Retorna: La incertidumbre combinada de las cuentas medida con el ADS1115 en [cuentas]
        """

        uA_Cx_cuentas = self.uA(std_dev)
        uB_Cx_cuentas = self.uB_ads_cuentas(cuentas_med)

        uC_Cx_cuentas = np.sqrt(uA_Cx_cuentas**2 + uB_Cx_cuentas**2)
        return uC_Cx_cuentas

    # Funcion principal de incertidumbre del ADS. Entran [cuentas] y devuelve [V]
    def uC_ads_voltage(self, cuentas_med, std_dev): # uC(Vx)
        """
        Calcula la incertidumbre combinada para una medición de tensión directa (ejemplo: Vce, Vbe).

        uC(Vx) = uR(Vx) * Vx_med
        uC(Vx) = sqrt(uR(Cx)**2 + uR(Vref)**2) * Vx_med

        Retorna: La incertidumbre combinada de la tension medida con el ADS1115 en [V]
        """

        uR_Cx = self.safe_div(self.uC_ads_cuentas(cuentas_med, std_dev), cuentas_med)
        uR_Vref = self.uB_ref_ads_rel

        Vx_med = self.CadsToVads(cuentas_med)

        uC_Vx = Vx_med * np.sqrt(uR_Cx**2 + uR_Vref**2)
        return uC_Vx

    # Entran [cuentas] y salen [A]
    def uC_ina_current(self, mean_val, std_dev):    # uC(Iina) [A]
        """
        Calcula la incertidumbre combinada para la corriente de Colector (Ic) medida con INA219.

        uC(Ix) = Ix_med * sqrt(uR(Cx)**2 + uR(Rshunt)**2)
        uR(Cx) = sqrt(uA(Cx)**2 + uB(Cx)**2) / mean_val
        """
        # CUENTAS
        uA_cuentas = self.uA(std_dev)
        uB_cuentas = self.uB_ina_cuentas(mean_val)
        uR_cuentas = self.safe_div(np.sqrt(uA_cuentas**2 + uB_cuentas**2), mean_val)

        # CORRIENTE
        Ix_med = self.CinaToAina(mean_val)

        # FINAL
        # uC_Amper = np.sqrt(uA_cuentas**2 + uB_cuentas**2) * Ix_med / mean_val # No entiendo el dividir denuevo por mean_val que son cuentas

        uC_Amper = Ix_med * np.sqrt(uR_cuentas**2 + self.uR_Rshunt_ina**2)
        return uC_Amper

    def calculos_Ib_ucurrent(self, V1_shunt, V1_shunt_s, V2_shunt, V2_shunt_s): # [uA]
        """
        Devuelve en uA la media de la corriente de base y su incertidumbre combinada.
        """
        Ib = self.CadsToVads(V1_shunt - V2_shunt) / self.r_shunt_b
        u_Ib = self.uC_base_current(V1_shunt, V1_shunt_s, V2_shunt, V2_shunt_s)

        # Se pasa todo a micro [uA]
        Ib = Ib * 1e6
        u_Ib = u_Ib * 1e6

        return Ib, u_Ib


    def uC_base_current(self, v1_med_cuentas, std_dev_v1_cuentas, v2_med_cuentas, std_dev_v2_cuentas):
        """
        Calcula la incertidumbre combinada para la corriente de Base (Ib).

        Funcion de medicion:    Ib = (V1 - V2) / R_shunt

        Aplica propagación de errores sobre:
        - Incertidumbre de V1 y V2
        - Incertidumbre de R_shunt (tolerancia)
        """
        # 1. Obtener incertidumbres combinadas de los voltajes individuales
        uC_v1 = self.uC_ads_voltage(v1_med_cuentas, std_dev_v1_cuentas)
        uC_v2 = self.uC_ads_voltage(v2_med_cuentas, std_dev_v2_cuentas)

        # 2. Derivadas
        # dIb / dV1 = 1 / R
        # dIb / dV2 = - 1 / R
        # dIb / dR  = - (V1 - V2) / R^2 = - Ib / R

        # Media
        #TODO: Agrego la conversión de cuentas de tension a tension
        ib_med = self.CadsToVads(v1_med_cuentas - v2_med_cuentas) / self.r_shunt_b

        # 3. Suma en cuadratura (los signos se van con los cuadrados)
        term_v1 = (uC_v1 / self.r_shunt_b)
        term_v2 = -(uC_v2 / self.r_shunt_b)
        term_r  = -(ib_med / self.r_shunt_b) * (self.uR_Rshunt_b * self.r_shunt_b)  #TODO: La incertidumbre de la rshunt debe ser absoluta, no relativa

        uC_ib = np.sqrt(term_v1**2 + term_v2**2 + term_r**2)

        return uC_ib

    def HFE(self, IC_mA, IB_uA):    # HFE [-]
        """
        Calcula el HFE con la corriente de colector y base.

        Funcion de medicion:    HFE = IC / IB
        """
        HFE = np.abs(self.safe_div(IC_mA, (IB_uA / 1000.0)))

        return HFE
    
    
    def uC_HFE(self, IC_med_mA, uC_IC_mA, IB_med_uA, uC_IB_uA): # uC_HFE [-]
        """
        Calcula la incertidumbre combinada del HFE con la corriente de colector y base.

        Funcion de medicion:    HFE = IC / IB
        """

        uC_IB_rel = self.safe_div(uC_IB_uA, IB_med_uA)

        uC_IC_rel = self.safe_div(uC_IC_mA, IC_med_mA)
        
        HFE_med = self.HFE(IC_med_mA, IB_med_uA)

        uC_HFE = np.sqrt(uC_IC_rel**2 + uC_IB_rel**2) * HFE_med
        
        return uC_HFE