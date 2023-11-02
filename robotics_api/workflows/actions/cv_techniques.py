import math
import sys
import time
import copy
import json
import pint
import datetime
import warnings
import numpy as np
import pandas as pd
from dataclasses import dataclass
from scipy.stats import linregress

try:
    import kbio.kbio_types as KBIO
    from kbio.kbio_api import KBIO_api
    from kbio.tech_types import TECH_ID
    from kbio.kbio_tech import ECC_parm, make_ecc_parm, make_ecc_parms, print_experiment_data
except ModuleNotFoundError:
    warnings.warn("KBIO module not imported.")
from robotics_api.standard_variables import *

VERBOSITY = 1


@dataclass
class current_step:
    current: float
    duration: float
    vs_init: bool = False


@dataclass
class voltage_step:
    voltage: float
    scan_rate: float
    vs_init: bool = False


def generate_col_params(voltage_sequence, scan_rate, volt_unit="V", scan_unit="V/s"):
    ureg = pint.UnitRegistry()

    # Get voltages with appropriate units
    voltages = voltage_sequence.split(',')
    voltage_units = ureg(voltages[-1]).units
    for i, v in enumerate(voltages):
        v_unit = "{}{}".format(v, voltage_units) if v.replace(".", "").replace("-", "").strip(" ").isnumeric() else v
        v_unit = ureg(v_unit)
        voltages[i] = v_unit.to(volt_unit).magnitude

    # Get scan rate with appropriate units
    scan_rate = ureg(scan_rate).to(scan_unit).magnitude
    collection_params = [dict(voltage=v, scan_rate=scan_rate) for v in voltages]
    return collection_params


class PotentiostatExperiment:
    def __init__(self, nb_words, time_out=TIME_OUT, load_firm=True, cut_beginning=0, cut_end=0,
                 potentiostat_address=POTENTIOSTAT_A_ADDRESS, potentiostat_channel=1):
        self.nb_words = nb_words  # number of rows for parsing
        self.k_api = KBIO_api(ECLIB_DLL_PATH)
        self.id_, self.d_info = self.k_api.Connect(potentiostat_address, time_out)
        self.potent_address = potentiostat_address
        self.potent_channel = potentiostat_channel
        self.cut_beginning = cut_beginning
        self.cut_end = cut_end
        self.time_out = time_out
        self.is_VMP3 = self.d_info.model in KBIO.VMP3_FAMILY
        self.is_VMP300 = self.d_info.model in KBIO.VMP300_FAMILY

        self.data = []
        self.steps = []
        self.params = {}
        self.record_every_de = None
        self.load_firm = load_firm
        self.scan_rate = None

    @staticmethod
    def normalize_steps(steps: list, data_class, min_steps=None):
        norm_steps = []
        for step in steps:
            if isinstance(steps, object):
                norm_steps.append(step)
            elif isinstance(steps, list):
                if 1 < len(steps) < 4:
                    norm_steps.append(data_class(*step))
                else:
                    print("WARNING: Each experiment step must a list of 2 or 3 items.")
            else:
                print("WARNING: Each experiment step must be a 'current_step' object or a list.")
        if min_steps:
            num_new_steps = min_steps - len(norm_steps)
            last_step = copy.deepcopy(norm_steps[-1])
            new_steps = [last_step for _ in range(num_new_steps)]
            norm_steps.extend(new_steps)
        if VERBOSITY:
            print("-------STEPS-------")
            [print(s) for s in norm_steps]
        return norm_steps

    def iR_comp(self,
                amplitude_voltage=0.5,  # Set this manually
                final_frequency=5000,
                initial_frequency=500,
                average_n_times=5,
                wait_for_steady=0,
                sweep=True,
                rcomp_level=RCOMP_LEVEL,
                rcmp_mode=0,  # always software unless an SP-300 series and running loop function
                ):
        iR_params = {
            'final_frequency': ECC_parm("Final_frequency", float),
            'initial_frequency': ECC_parm("Initial_frequency", float),
            'amplitude_voltage': ECC_parm("Amplitude_Voltage", float),
            'average_n_times': ECC_parm("Average_N_times", int),
            'wait_for_steady': ECC_parm("Wait_for_steady", float),
            'sweep': ECC_parm("sweep", bool),
            'rcomp_level': ECC_parm("Rcomp_Level", float),
            # 'rcmp_mode': ECC_parm("Rcmp_Mode", int),
        }

        exp_params = list()

        exp_params.append(make_ecc_parm(self.k_api, iR_params['final_frequency'], final_frequency))
        exp_params.append(make_ecc_parm(self.k_api, iR_params['initial_frequency'], initial_frequency))
        exp_params.append(make_ecc_parm(self.k_api, iR_params['amplitude_voltage'], amplitude_voltage))
        exp_params.append(make_ecc_parm(self.k_api, iR_params['average_n_times'], average_n_times))
        exp_params.append(make_ecc_parm(self.k_api, iR_params['wait_for_steady'], wait_for_steady))
        exp_params.append(make_ecc_parm(self.k_api, iR_params['sweep'], sweep))
        exp_params.append(make_ecc_parm(self.k_api, iR_params['rcomp_level'], rcomp_level))
        # exp_params.append(make_ecc_parm(self.k_api, iR_params['rcmp_mode'], rcmp_mode))

        # make the technique parameter array
        ecc_params = make_ecc_parms(self.k_api, *exp_params)
        tech_file = 'pzir.ecc' if self.is_VMP3 else 'pzir4.ecc'
        return ecc_params, tech_file

    def check_connection(self):
        conn = self.k_api.TestConnection(self.id_)
        if not conn:
            print(f"> device[{self.potent_address}] must be connected to run the experiment")
            return False
        # BL_GetChannelInfos
        channel_info = self.k_api.GetChannelInfo(self.id_, self.potent_channel)
        # BL_LoadFirmware
        if channel_info.has_no_firmware and self.load_firm:
            print("No firmware loaded.")
            self.load_firmware()
        return True

    def check_kernel(self):
        # BL_GetChannelInfos
        channel_info = self.k_api.GetChannelInfo(self.id_, self.potent_channel)
        if not channel_info.is_kernel_loaded:
            print("> kernel must be loaded in order to run the experiment")
            sys.exit(-1)

    def load_firmware(self):
        if self.is_VMP3:
            firmware_path = "kernel.bin"
            fpga_path = "Vmp_ii_0437_a6.xlx"
        elif self.is_VMP300:
            firmware_path = "kernel4.bin"
            fpga_path = "vmp_iv_0395_aa.xlx"
        else:
            firmware_path = None
            fpga_path = None
        print(f"> Loading {firmware_path} ...")
        # create a map from channel set
        channel_map = self.k_api.channel_map({self.potent_channel})
        # BL_LoadFirmware
        self.k_api.LoadFirmware(self.id_, channel_map, firmware=firmware_path, fpga=fpga_path, force=True)

    def print_messages(self):
        while True:
            msg = self.k_api.GetMessage(self.id_, self.potent_channel)
            if not msg:
                break
            print(msg)

    @property
    def tech_file(self):
        return ''

    def experiment_print(self, data_info, data_record):
        return None

    def run_experiment(self):
        try:
            if not self.check_connection():
                self.id_, self.d_info = self.k_api.Connect(self.potent_address, self.time_out)  # Connect

            # Clear Data
            self.data = []
            ir_comp_params, ir_tech = self.iR_comp()
            # BL_LoadTechnique
            print(self.id_)

            self.k_api.LoadTechnique(self.id_, self.potent_channel, ir_tech, ir_comp_params, first=True, last=False,
                                     display=(VERBOSITY > 1))
            self.k_api.LoadTechnique(self.id_, self.potent_channel, self.tech_file, self.params, first=False, last=True,
                                     display=(VERBOSITY > 1))
            # BL_StartChannel
            self.k_api.StartChannel(self.id_, self.potent_channel)

            # experiment loop
            print("Start {} cycle...".format(self.tech_file[:-4]))
            while True:
                # BL_GetData
                exp_data = self.k_api.GetData(self.id_, self.potent_channel)
                self.data.append(exp_data)
                current_values, data_info, data_record = exp_data

                if VERBOSITY:
                    self.experiment_print(data_info, data_record)

                status = KBIO.PROG_STATE(current_values.State).name

                print("> new messages :")
                self.print_messages()
                if status == 'STOP':
                    break
                time.sleep(1)
            print("> experiment done")
        except KeyboardInterrupt:
            print(".. interrupted")

        # BL_Disconnect
        self.k_api.Disconnect(self.id_)

    @property
    def parsed_data(self):
        return []

    def save_parsed_data(self, out_file):
        with open(out_file, 'w') as f:
            json.dump(self.parsed_data, f)

    def to_txt(self, outfile, header='', note=''):
        extracted_data = self.parsed_data

        # Cut front and back ends off data
        orig_times = [s["t"] for s in extracted_data]
        min_idx, max_idx = int(len(orig_times) * self.cut_beginning), int(len(orig_times) * (1 - self.cut_end))

        # Collect data
        times = [s["t"] for s in extracted_data][min_idx:max_idx]
        voltages = [s["Ewe"] for s in extracted_data][min_idx:max_idx]
        currents = [s["I"] for s in extracted_data][min_idx:max_idx]

        # Scan rate
        if not getattr(self, "scan_rate", None):
            # TODO fix this scan rate calculator
            forward_idx = [i for i, _ in enumerate(voltages[:-1]) if voltages[i] > voltages[i + 1]]
            forward_volt, forward_time = [voltages[i] for i in forward_idx], [times[i] for i in forward_idx]
            self.scan_rate = linregress(forward_time, forward_volt)[0]

        with open(outfile, 'w') as f:
            f.write(datetime.datetime.now().strftime("%c") + "\n")
            f.write("Cyclic Voltammetry\n")
            f.write("File: {}\n".format(outfile))
            f.write("Data Source: KBIO Potentiostat\n")
            f.write("Instrument Model: {}\n".format(self.d_info.model))
            f.write("Header: {}\n".format(header))
            f.write("Note: {}\n\n".format(note))
            f.write("Init E (V) = {:.2f}\n".format(voltages[0]))
            f.write("High E (V) = {:.2f}\n".format(max(voltages)))
            f.write("Low E (V) = {:.2f}\n".format(min(voltages)))
            # fn.write("Init P/N = {}\n".format(''))
            f.write("Scan Rate (V/s) = {:.3f}\n".format(float(self.scan_rate)))
            f.write("Segment = {}\n".format(len(self.steps)))
            f.write("Sample Interval (V) = {:.3e}\n".format(self.record_every_de or np.average(np.diff(voltages))))
            # fn.write("Quiet Time (sec) = {}\n".format(''))
            # fn.write("Sensitivity (A/V) = {}\n".format(''))
            f.write("\n")
            f.write("Potential/V, Current/A\n")
            f.writelines(["{:.3e}, {:.3e}\n".format(v, i) for v, i in zip(voltages, currents)])


class iRCompExperiment(PotentiostatExperiment):
    # TODO documentation
    def __init__(self,
                 amplitude_voltage=0.5,  # Set this manually
                 final_frequency=5000,
                 initial_frequency=500,
                 average_n_times=5,
                 wait_for_steady=0,
                 sweep=True,
                 rcomp_level=RCOMP_LEVEL,
                 rcmp_mode=0,  # always software unless an SP-300 series and running loop function
                 **kwargs):
        super().__init__(15, **kwargs)

        # Initialize Parameters
        self.final_frequency = final_frequency
        self.initial_frequency = initial_frequency
        self.amplitude_voltage = amplitude_voltage
        self.average_n_times = average_n_times
        self.wait_for_steady = wait_for_steady
        self.sweep = sweep
        self.rcomp_level = rcomp_level
        self.rcmp_mode = rcmp_mode

        # Set Parameters
        self.params = self.parameterize()
        self.data = []

    @property
    def tech_file(self):
        # pick the correct ecc file based on the instrument family
        return 'pzir.ecc' if self.is_VMP3 else 'pzir4.ecc'

    def parameterize(self):
        iR_params = {
            'final_frequency': ECC_parm("Final_frequency", float),
            'initial_frequency': ECC_parm("Initial_frequency", float),
            'amplitude_voltage': ECC_parm("Amplitude_Voltage", float),
            'average_n_times': ECC_parm("Average_N_times", int),
            'wait_for_steady': ECC_parm("Wait_for_steady", float),
            'sweep': ECC_parm("sweep", bool),
            'rcomp_level': ECC_parm("Rcomp_Level", float),
            # 'rcmp_mode': ECC_parm("Rcmp_Mode", int),
        }

        exp_params = list()

        exp_params.append(make_ecc_parm(self.k_api, iR_params['final_frequency'], self.final_frequency))
        exp_params.append(make_ecc_parm(self.k_api, iR_params['initial_frequency'], self.initial_frequency))
        exp_params.append(make_ecc_parm(self.k_api, iR_params['amplitude_voltage'], self.amplitude_voltage))
        exp_params.append(make_ecc_parm(self.k_api, iR_params['average_n_times'], self.average_n_times))
        exp_params.append(make_ecc_parm(self.k_api, iR_params['wait_for_steady'], self.wait_for_steady))
        exp_params.append(make_ecc_parm(self.k_api, iR_params['sweep'], self.sweep))
        exp_params.append(make_ecc_parm(self.k_api, iR_params['rcomp_level'], self.rcomp_level))
        # exp_params.append(make_ecc_parm(self.k_api, iR_params['rcmp_mode'], self.rcmp_mode))

        # make the technique parameter array
        ecc_params = make_ecc_parms(self.k_api, *exp_params)
        return ecc_params

    @property
    def parsed_data(self, strict_error=False):
        extracted_data = []
        for data_step in self.data:
            current_values, data_info, data_record = data_step
            tech_name = TECH_ID(data_info.TechniqueID).name
            if data_info.NbCols != self.nb_words:
                if strict_error:
                    raise RuntimeError(f"{tech_name} : unexpected record length ({data_info.NbCols})")
                continue
            ix = 0
            for _ in range(data_info.NbRows):
                # progress through record
                inx = ix + data_info.NbCols
                row = data_record[ix:inx]
                f, abs_Ewe, abs_I, phase_Zwe, ewe_raw, i_raw, _, \
                    abs_Ece, abs_Ice, phase_Zce, ece_raw, _, _, t, i_range = row

                # compute timestamp in seconds
                t = self.k_api.ConvertNumericIntoSingle(t)
                # Ewe and current as floats
                Freq = self.k_api.ConvertNumericIntoSingle(f)
                abs_Ewe = self.k_api.ConvertNumericIntoSingle(abs_Ewe)
                abs_Ece = self.k_api.ConvertNumericIntoSingle(abs_Ece)
                abs_I = self.k_api.ConvertNumericIntoSingle(abs_I)
                abs_Ice = self.k_api.ConvertNumericIntoSingle(abs_Ice)
                i = self.k_api.ConvertNumericIntoSingle(i_raw)
                i_range = self.k_api.ConvertNumericIntoSingle(i_range)
                phase_Zwe = self.k_api.ConvertNumericIntoSingle(phase_Zwe)
                phase_Zce = self.k_api.ConvertNumericIntoSingle(phase_Zce)
                Ewe = self.k_api.ConvertNumericIntoSingle(ewe_raw)
                Ece = self.k_api.ConvertNumericIntoSingle(ece_raw)
                abs_res = abs_Ewe / abs_I
                real_ = abs_res * math.cos(phase_Zwe)
                imaginary_ = abs(abs_res * math.sin(phase_Zwe))

                extracted_data.append({'t': t, 'Ewe': Ewe, 'Ece': Ece, 'I': i, 'freq': Freq, 'abs_ewe': abs_Ewe,
                                       'abs_ece': abs_Ece, 'abs_iwe': abs_I, 'abs_ice': abs_Ice, 'i_range': i_range,
                                       'phase_zwe': phase_Zwe, 'phase_zce': phase_Zce, 'real': real_,
                                       'imag': imaginary_})
                ix = inx

        return extracted_data

    def to_txt(self, outfile, header='', note=''):
        extracted_data = self.parsed_data
        df = pd.DataFrame(extracted_data)
        df.to_csv(outfile)

    def experiment_print(self, data_step):
        # TODO CHANGE
        current_values, data_info, data_record = data_step
        print("-------------------time / frequency-------------------------")
        ix = 0
        for _ in range(data_info.NbRows):
            # progress through record
            inx = ix + data_info.NbCols
            # extract timestamp and one row
            row = data_record[ix:inx]
            t = self.k_api.ConvertNumericIntoSingle(row[-2])
            freq = self.k_api.ConvertNumericIntoSingle(row[0])
            print('-------------------{} / {}-------------------------'.format(t, freq))
            ix = inx


class EisExperiment(PotentiostatExperiment):
    # TODO documentation
    def __init__(self,
                 vs_initial=0,  # depends on the molecule
                 vs_final=0,  # depends on the molecule
                 Initial_Voltage_step=0.1,
                 Final_Voltage_step=0.1,
                 Duration_step=0.5,
                 Step_number=41,
                 Record_every_dT=0.25,
                 Record_every_dI=0.1,
                 Final_frequency=0,
                 Initial_frequency=0,
                 sweep=False,
                 Amplitude_Voltage=0.01,
                 Frequency_number=10,
                 Average_N_times=5,
                 Correction=False,
                 Wait_for_steady=0.1,
                 **kwargs):
        super().__init__(15, **kwargs)

        # Initialize Parameters
        self.vs_initial = vs_initial
        self.vs_final = vs_final
        self.Initial_Voltage_step = Initial_Voltage_step
        self.Final_Voltage_step = Final_Voltage_step
        self.Duration_step = Duration_step
        self.Step_number = Step_number
        self.Record_every_dT = Record_every_dT
        self.Record_every_dI = Record_every_dI
        self.Final_frequency = Final_frequency
        self.Initial_frequency = Initial_frequency
        self.sweep = sweep
        self.Amplitude_Voltage = Amplitude_Voltage
        self.Frequency_number = Frequency_number
        self.Average_N_times = Average_N_times
        self.Correction = Correction
        self.Wait_for_steady = Wait_for_steady

        # Set Parameters
        self.params = self.parameterize()
        self.data = []

    @property
    def tech_file(self):
        # pick the correct ecc file based on the instrument family
        return 'peis.ecc' if self.is_VMP3 else 'peis4.ecc'

    def parameterize(self):
        eis_params = {
            'vs_initial': ECC_parm('vs_initial', bool),
            'vs_final': ECC_parm('vs_final', bool),
            'Initial_Voltage_step': ECC_parm('Initial_Voltage_step', float),
            'Final_Voltage_step': ECC_parm('Final_Voltage_step', float),
            'Duration_step': ECC_parm('Duration_step', float),
            'Step_number': ECC_parm('Step_number', int),
            'Record_every_dT': ECC_parm('Record_every_dT', float),
            'Record_every_dI': ECC_parm('Record_every_dI', float),
            'Final_frequency': ECC_parm('Final_frequency', float),
            'Initial_frequency': ECC_parm('Initial_frequency', float),
            'sweep': ECC_parm('sweep', bool),
            'Amplitude_Voltage': ECC_parm('Amplitude_Voltage', float),
            'Frequency_number': ECC_parm('Frequency_number', int),
            'Average_N_times': ECC_parm('Average_N_times', int),
            'Correction': ECC_parm('Correction', bool),
            'Wait_for_steady': ECC_parm('Wait_for_steady', float)
        }

        exp_params = list()

        exp_params.append(make_ecc_parm(self.k_api, eis_params['vs_initial'], self.vs_initial))
        exp_params.append(make_ecc_parm(self.k_api, eis_params['vs_final'], self.vs_final))
        exp_params.append(make_ecc_parm(self.k_api, eis_params['Initial_Voltage_step'], self.Initial_Voltage_step))
        exp_params.append(make_ecc_parm(self.k_api, eis_params['Final_Voltage_step'], self.Final_Voltage_step))
        exp_params.append(make_ecc_parm(self.k_api, eis_params['Duration_step'], self.Duration_step))
        exp_params.append(make_ecc_parm(self.k_api, eis_params['Step_number'], self.Step_number))
        exp_params.append(make_ecc_parm(self.k_api, eis_params['Record_every_dT'], self.Record_every_dT))
        exp_params.append(make_ecc_parm(self.k_api, eis_params['Record_every_dI'], self.Record_every_dI))
        exp_params.append(make_ecc_parm(self.k_api, eis_params['Final_frequency'], self.Final_frequency))
        exp_params.append(make_ecc_parm(self.k_api, eis_params['Initial_frequency'], self.Initial_frequency))
        exp_params.append(make_ecc_parm(self.k_api, eis_params['sweep'], self.sweep))
        exp_params.append(make_ecc_parm(self.k_api, eis_params['Amplitude_Voltage'], self.Amplitude_Voltage))
        exp_params.append(make_ecc_parm(self.k_api, eis_params['Frequency_number'], self.Frequency_number))
        exp_params.append(make_ecc_parm(self.k_api, eis_params['Average_N_times'], self.Average_N_times))
        exp_params.append(make_ecc_parm(self.k_api, eis_params['Correction'], self.Correction))
        exp_params.append(make_ecc_parm(self.k_api, eis_params['Wait_for_steady'], self.Wait_for_steady))

        # make the technique parameter array
        ecc_params = make_ecc_parms(self.k_api, *exp_params)
        return ecc_params

    @property
    def parsed_data(self, strict_error=False):
        extracted_data = []
        for data_step in self.data:
            current_values, data_info, data_record = data_step
            tech_name = TECH_ID(data_info.TechniqueID).name
            if data_info.NbCols != self.nb_words:
                if strict_error:
                    raise RuntimeError(f"{tech_name} : unexpected record length ({data_info.NbCols})")
                continue
            ix = 0
            for _ in range(data_info.NbRows):
                # progress through record
                inx = ix + data_info.NbCols
                row = data_record[ix:inx]
                f, abs_Ewe, abs_I, phase_Zwe, ewe_raw, i_raw, _, \
                    abs_Ece, abs_Ice, phase_Zce, ece_raw, _, _, t, i_range = row

                # compute timestamp in seconds
                t = self.k_api.ConvertNumericIntoSingle(t)
                # Ewe and current as floats
                Freq = self.k_api.ConvertNumericIntoSingle(f)
                abs_Ewe = self.k_api.ConvertNumericIntoSingle(abs_Ewe)
                abs_Ece = self.k_api.ConvertNumericIntoSingle(abs_Ece)
                abs_I = self.k_api.ConvertNumericIntoSingle(abs_I)
                abs_Ice = self.k_api.ConvertNumericIntoSingle(abs_Ice)
                i = self.k_api.ConvertNumericIntoSingle(i_raw)
                i_range = self.k_api.ConvertNumericIntoSingle(i_range)
                phase_Zwe = self.k_api.ConvertNumericIntoSingle(phase_Zwe)
                phase_Zce = self.k_api.ConvertNumericIntoSingle(phase_Zce)
                Ewe = self.k_api.ConvertNumericIntoSingle(ewe_raw)
                Ece = self.k_api.ConvertNumericIntoSingle(ece_raw)
                abs_res = abs_Ewe / abs_I
                real_ = abs_res * math.cos(phase_Zwe)
                imaginary_ = abs(abs_res * math.sin(phase_Zwe))
                extracted_data.append({'t': t, 'Ewe': Ewe, 'Ece': Ece, 'I': i, 'freq': Freq, 'abs_ewe': abs_Ewe,
                                       'abs_ece': abs_Ece, 'abs_iwe': abs_I, 'abs_ice': abs_Ice, 'i_range': i_range,
                                       'phase_zwe': phase_Zwe, 'phase_zce': phase_Zce, 'real_res': real_,
                                       'im_res': imaginary_})
                ix = inx

        return extracted_data

    def to_txt(self, outfile, header='', note=''):
        extracted_data = self.parsed_data
        df = pd.DataFrame(extracted_data)
        df.to_csv(outfile)

    def experiment_print(self, data_step):
        current_values, data_info, data_record = data_step
        print("-------------------time / frequency / real_res-------------------------")
        ix = 0
        for _ in range(data_info.NbRows):
            # progress through record
            inx = ix + data_info.NbCols
            if data_info.ProcessIndex == 0:
                pass
            else:
                # extract timestamp and one row
                row = data_record[ix:inx]
                t = self.k_api.ConvertNumericIntoSingle(row[-2])
                freq = self.k_api.ConvertNumericIntoSingle(row[0])
                i = self.k_api.ConvertNumericIntoSingle(row[5])
                ewe = self.k_api.ConvertNumericIntoSingle(row[4])
                phase_w = self.k_api.ConvertNumericIntoSingle(row[3])
                absres = i / ewe
                real = absres * math.cos(phase_w)
                print('-------------------{} / {} / {}-------------------------'.format(t, freq, real))
            ix = inx


class CpExperiment(PotentiostatExperiment):
    """
    Class to run Chrono-Potentiometry technique experiments
        :param n_cycles : Number of cycle, integer ≥ 0
        :param record_every_dt : recording on dt (s), float ≥ 0
        :param record_every_de : recording on dE (V), float ≥ 0
        :param i_range : kbio I_RANGE keyword, str
        :param time_out : time to wait, float
    """

    def __init__(self,
                 n_cycles=N_CYCLES,
                 record_every_dt=RECORD_EVERY_DT,  # seconds
                 record_every_de=RECORD_EVERY_DE,  # Volts
                 i_range=I_RANGE,
                 repeat_count=0,
                 **kwargs):
        super().__init__(3, **kwargs)

        self.record_every_dt = record_every_dt
        self.record_every_de = record_every_de
        self.i_range = i_range
        self.repeat_count = repeat_count
        self.n_cycles = n_cycles

        self.params = self.parameterize()

    @property
    def tech_file(self):
        # pick the correct ecc file based on the instrument family
        return "cp.ecc" if self.is_VMP3 else "cp4.ecc"

    def parameterize(self):
        # BL_Define<xxx>Parameter
        CP_params = {
            'current_step': ECC_parm("Current_step", float),
            'step_duration': ECC_parm("Duration_step", float),
            'vs_init': ECC_parm("vs_initial", bool),
            'nb_steps': ECC_parm("Step_number", int),
            'record_dt': ECC_parm("Record_every_dT", float),
            'record_dE': ECC_parm("Record_every_dE", float),
            'repeat': ECC_parm("N_Cycles", int),
            'I_range': ECC_parm("I_Range", int),
        }
        idx = 0
        exp_params = list()

        for idx, step in enumerate(self.steps):
            parm = make_ecc_parm(self.k_api, CP_params['current_step'], step.current, idx)
            exp_params.append(parm)
            parm = make_ecc_parm(self.k_api, CP_params['step_duration'], step.duration, idx)
            exp_params.append(parm)
            parm = make_ecc_parm(self.k_api, CP_params['vs_init'], step.vs_init, idx)
            exp_params.append(parm)

        # number of steps is one less than len(steps)
        exp_params.append(make_ecc_parm(self.k_api, CP_params['nb_steps'], idx))

        # record parameters
        exp_params.append(make_ecc_parm(self.k_api, CP_params['record_dt'], self.record_every_dt))
        exp_params.append(make_ecc_parm(self.k_api, CP_params['record_dE'], self.record_every_de))

        # repeating factor
        exp_params.append(make_ecc_parm(self.k_api, CP_params['repeat'], self.repeat_count))
        exp_params.append(make_ecc_parm(self.k_api, CP_params['I_range'], KBIO.I_RANGE[self.i_range].value))

        # make the technique parameter array
        ecc_params = make_ecc_parms(self.k_api, *exp_params)
        return ecc_params

    @property
    def parsed_data(self):
        extracted_data = []
        for data_step in self.data:
            current_values, data_info, data_record = data_step
            tech_name = TECH_ID(data_info.TechniqueID).name
            ix = 0
            for _ in range(data_info.NbRows):

                # progress through record
                inx = ix + data_info.NbCols

                # extract timestamp and one row
                t_high, t_low, *row = data_record[ix:inx]
                # compute timestamp in seconds
                t_rel = (t_high << 32) + t_low
                t = current_values.TimeBase * t_rel

                nb_words = len(row)
                if nb_words != self.nb_words:
                    raise RuntimeError(f"{tech_name} : unexpected record length ({nb_words})")

                # Ewe is a float
                Ewe = self.k_api.ConvertNumericIntoSingle(row[0])

                # current is a float
                i = self.k_api.ConvertNumericIntoSingle(row[1])

                # technique cycle is an integer
                cycle = row[2]

                extracted_data.append({'t': t, 'Ewe': Ewe, 'I': i, 'cycle': cycle})
                ix = inx
        return extracted_data

    def experiment_print(self, data_step):
        current_values, data_info, data_record = data_step
        print("-------------------STEP-------------------")
        ix = 0
        for _ in range(data_info.NbRows):
            # progress through record
            inx = ix + data_info.NbCols
            # extract timestamp and one row
            t_high, t_low, *row = data_record[ix:inx]
            Ewe = self.k_api.ConvertNumericIntoSingle(row[0])
            print(Ewe)
            ix = inx


class CvExperiment(PotentiostatExperiment):
    """
    Class to run cyclic voltammetry experiments
        :param steps : list of lists OR current_step objects: voltage (V), scan_rate (mV/s))
        :param scan_number : Scan number, integer = 2
        :param vs_initial : Current step vs initial one, bool
        :param record_every_de : recording on dE (V), float ≥ 0
        :param n_cycles : Number of cycle, integer ≥ 0
        :param time_out : time to wait, float
    """

    def __init__(self,
                 steps: list,
                 vs_initial=VS_INITIAL,
                 n_cycles=N_CYCLES,
                 scan_number=SCAN_NUMBER,
                 record_every_de=RECORD_EVERY_DE,
                 average_over_de=AVERAGE_OVER_DE,
                 min_steps=MIN_CV_STEPS,
                 rcomp_level=RCOMP_LEVEL,
                 **kwargs):
        super().__init__(6, **kwargs)

        # Set Parameters
        self.steps = self.normalize_steps(steps, voltage_step, min_steps=min_steps)
        self.scan_number = scan_number
        self.vs_initial = vs_initial
        self.record_every_de = record_every_de
        self.average_over_de = average_over_de
        self.n_cycles = n_cycles
        self.rcomp_level = rcomp_level  # TODO figure out iR comp

        self.params = self.parameterize()
        self.data = []

        # Set Parameters

    @property
    def tech_file(self):
        # pick the correct ecc file based on the instrument family
        return 'cv.ecc' if self.is_VMP3 else 'cv4.ecc'

    def parameterize(self):
        CV_params = {
            'vs_initial': ECC_parm("vs_initial", bool),
            'voltage_step': ECC_parm("Voltage_step", float),
            'scan_rate': ECC_parm("Scan_Rate", float),
            'scan_number': ECC_parm("Scan_number", float),
            'record_every_de': ECC_parm("Record_every_dE", float),
            'average_over_de': ECC_parm("Average_over_dE", bool),
            'n_cycles': ECC_parm("N_Cycles", int),
            'Begin_measuring_I': ECC_parm("I_Range", float),  # Don't set (use default)
            'End_measuring_I': ECC_parm("I_Range", float),  # Don't set (use default)
        }

        exp_params = list()
        scan_rates = []
        for _idx, step in enumerate(self.steps):
            parm = make_ecc_parm(self.k_api, CV_params['voltage_step'], step.voltage, _idx)
            exp_params.append(parm)
            scan_rates.append(step.scan_rate)
            parm = make_ecc_parm(self.k_api, CV_params['scan_rate'], step.scan_rate, _idx)
            exp_params.append(parm)
            parm = make_ecc_parm(self.k_api, CV_params['vs_initial'], step.vs_init, _idx)
            exp_params.append(parm)
        self.scan_rate = scan_rates[0] if len(set(scan_rates)) == 1 else None

        # repeating factor
        exp_params.append(make_ecc_parm(self.k_api, CV_params['n_cycles'], self.n_cycles))
        # exp_params.append(make_ecc_parm(self.k_api, CV_params['scan_number'], self.scan_number))

        # record parameters:
        exp_params.append(make_ecc_parm(self.k_api, CV_params['record_every_de'], self.record_every_de))
        exp_params.append(make_ecc_parm(self.k_api, CV_params['average_over_de'], self.average_over_de))
        # exp_params.append(make_ecc_parm(self.k_api, CV_params['Begin_measuring_I'], 0.8))
        # exp_params.append(make_ecc_parm(self.k_api, CV_params['End_measuring_I'], 0.8))

        # make the technique parameter array
        ecc_params = make_ecc_parms(self.k_api, *exp_params)
        return ecc_params

    @property
    def parsed_data(self):
        extracted_data = []
        for data_step in self.data:
            current_values, data_info, data_record = data_step
            tech_name = TECH_ID(data_info.TechniqueID).name
            if data_info.NbCols != self.nb_words:
                raise RuntimeError(f"{tech_name} : unexpected record length ({data_info.NbCols})")

            ix = 0
            for _ in range(data_info.NbRows):
                # progress through record
                inx = ix + data_info.NbCols
                row = data_record[ix:inx]
                if self.is_VMP3:
                    t_high, t_low, ec_raw, i_raw, ewe_raw, cycle = row
                    Ec = self.k_api.ConvertNumericIntoSingle(ec_raw)
                else:
                    t_high, t_low, i_raw, ewe_raw, cycle = row
                    Ec = None

                # compute timestamp in seconds
                t = current_values.TimeBase * (t_high << 32) + t_low
                # Ewe and current as floats
                Ewe = self.k_api.ConvertNumericIntoSingle(ewe_raw)
                curr = self.k_api.ConvertNumericIntoSingle(i_raw)

                extracted_data.append({'t': t, 'Ewe': Ewe, 'Ec': Ec, 'I': curr, 'cycle': cycle})
                ix = inx
        return extracted_data

    def experiment_print(self, data_step):
        current_values, data_info, data_record = data_step
        print("-------------------STEP-------------------")
        ix = 0
        for _ in range(1, data_info.NbRows):
            inx = ix + data_info.NbCols
            try:
                if self.is_VMP3:
                    t_high, t_low, ec_raw, i_raw, ewe_raw, cycle = data_record[ix:inx]
                else:
                    t_high, t_low, i_raw, ewe_raw, cycle = data_record[ix:inx]

                print("Volt:  {:02f} \t Current:  {:.2E}".format(self.k_api.ConvertNumericIntoSingle(ewe_raw),
                                                                 self.k_api.ConvertNumericIntoSingle(i_raw)))
            except:
                pass

            ix = inx


class CaExperiment(PotentiostatExperiment):
    # TODO Documentation

    def __init__(self,
                 steps=[0.025, -0.025] * 50,
                 vs_initial=[True, False] * 50,
                 duration_step=[0.000024] * 100,
                 step_number=98,
                 record_every_dt=0.000024,
                 record_every_di=0.1,
                 n_cycles=2,
                 **kwargs):
        super().__init__(5, **kwargs)

        # Set Parameters
        self.steps = steps
        self.vs_initial = vs_initial
        self.duration = duration_step
        self.step_number = step_number
        self.record_every_dt = record_every_dt
        self.record_every_di = record_every_di
        self.n_cycles = n_cycles

        self.params = self.parameterize()
        self.data = []

        # Set Parameters

    @property
    def tech_file(self):
        # pick the correct ecc file based on the instrument family
        return 'ca.ecc' if self.is_VMP3 else 'ca4.ecc'

    def parameterize(self):
        Ca_params = {
            'voltage_step': ECC_parm("Voltage_step", float),
            'vs_initial': ECC_parm("vs_initial", bool),
            'duration_step': ECC_parm("Duration_step", float),
            'step_number': ECC_parm("Step_number", int),
            'record_every_dT': ECC_parm("Record_every_dT", float),
            'record_every_dI': ECC_parm("Record_every_dI", float),
            'n_cycles': ECC_parm("N_Cycles", int),
        }

        exp_params = list()
        scan_rates = []
        for _idx, step in enumerate(self.steps):
            parm = make_ecc_parm(self.k_api, Ca_params['voltage_step'], step, _idx)
            exp_params.append(parm)
        for _idx, voltage in enumerate(self.vs_initial):
            parm = make_ecc_parm(self.k_api, Ca_params['vs_initial'], voltage, _idx)
            exp_params.append(parm)
        for _idx, duration in enumerate(self.duration):
            parm = make_ecc_parm(self.k_api, Ca_params['duration_step'], duration, _idx)
            exp_params.append(parm)

        # repeating factor
        exp_params.append(make_ecc_parm(self.k_api, Ca_params['n_cycles'], self.n_cycles))
        # exp_params.append(make_ecc_parm(self.k_api, CV_params['scan_number'], self.scan_number))

        # record parameters:
        exp_params.append(make_ecc_parm(self.k_api, Ca_params['record_every_dT'], self.record_every_dt))
        exp_params.append(make_ecc_parm(self.k_api, Ca_params['record_every_dI'], self.record_every_di))
        exp_params.append(make_ecc_parm(self.k_api, Ca_params['step_number'], self.step_number))
        # exp_params.append(make_ecc_parm(self.k_api, CV_params['Begin_measuring_I'], 0.8))
        # exp_params.append(make_ecc_parm(self.k_api, CV_params['End_measuring_I'], 0.8))

        # make the technique parameter array
        ecc_params = make_ecc_parms(self.k_api, *exp_params)
        return ecc_params

    @property
    def parsed_data(self):
        extracted_data = []
        for data_step in self.data:
            current_values, data_info, data_record = data_step
            tech_name = TECH_ID(data_info.TechniqueID).name
            if data_info.NbCols != self.nb_words:
                raise RuntimeError(f"{tech_name} : unexpected record length ({data_info.NbCols})")

            ix = 0
            for _ in range(data_info.NbRows):
                # progress through record
                inx = ix + data_info.NbCols
                row = data_record[ix:inx]
                if self.is_VMP3:
                    t_high, t_low, ewe_raw, i_raw, cycle = row
                else:
                    t_high, t_low, i_raw, ewe_raw, cycle = row

                # compute timestamp in seconds
                t = current_values.TimeBase * ((t_high << 32) + t_low)
                # Ewe and current as floats
                Ewe = self.k_api.ConvertNumericIntoSingle(ewe_raw)
                curr = self.k_api.ConvertNumericIntoSingle(i_raw)
                extracted_data.append({'t': t, 'Ewe': Ewe, 'I': curr, 'cycle': cycle})
                ix = inx
        return extracted_data

    def experiment_print(self, data_step):
        current_values, data_info, data_record = data_step
        print("-------------------STEP-------------------")
        ix = 0
        for _ in range(data_info.NbRows):
            inx = ix + data_info.NbCols
            if self.is_VMP3:
                t_high, t_low, i_raw, ewe_raw, cycle = data_record[ix:inx]
            else:
                t_high, t_low, i_raw, ewe_raw, cycle = data_record[ix:inx]

            print("Time:  {} \t Volt:  {:02f} \t Current:  {:.2E}".format(
                current_values.TimeBase * ((t_high << 32) + t_low),
                self.k_api.ConvertNumericIntoSingle(ewe_raw),
                self.k_api.ConvertNumericIntoSingle(i_raw)))
            ix = inx


def cp_ex():
    cp_steps = [
        current_step(0.001, 2),  # 1mA during 2s
        current_step(0.002, 1),  # 2mA during 1s
        current_step(0.0005, 3, True),  # 0.5mA delta during 3s
    ]
    cp_exp = CpExperiment(cp_steps)
    cp_exp.run_experiment()
    cp_exp.to_txt("cp_example.txt")


def cv_ex(scan_rate=0.500, r_comp=RCOMP_LEVEL, potentiostat_address=POTENTIOSTAT_A_ADDRESS, potentiostat_channel=2):
    collection_params = [{"voltage": 0., "scan_rate": scan_rate},
                         {"voltage": 0.7, "scan_rate": scan_rate},
                         {"voltage": -0.3, "scan_rate": scan_rate},
                         {"voltage": 0, "scan_rate": scan_rate}]
    ex_steps = [voltage_step(**p) for p in collection_params]
    exp = CvExperiment(ex_steps, rcomp_level=r_comp,
                       potentiostat_address=potentiostat_address, potentiostat_channel=potentiostat_channel)
    exp.run_experiment()
    data = exp.data
    with open('examples/iR_testing/link_data_nov_2.txt', 'a') as f:
        for data_step in data:
            current_values, data_info, data_record = data_step
            data_record_converted = []
            for i in data_record:
                try:
                    record = KBIO_api(ECLIB_DLL_PATH).ConvertNumericIntoSingle(i)
                except:
                    record = i
                data_record_converted.append(record)
            f.write(str(data_record_converted))
        f.write(" \n \n")
        f.close()
    parsed_data = exp.parsed_data
    # potentials = [s["Ewe"] for s in parsed_data]
    # current = [s["I"] for s in parsed_data]
    #
    # import matplotlib.pyplot as plt
    # plt.scatter(potentials, current)
    # plt.ylabel("Current")
    # plt.xlabel("Voltage")
    # plt.savefig("examples/cv_example.png")
    # exp.save_parsed_data("examples/cv_data_example.json")
    # exp.to_txt("examples/cv_example.csv")


def ir_comp_ex(potentiostat_address=POTENTIOSTAT_A_ADDRESS, potentiostat_channel=2, vs_initial_eis=None,
               vs_final_eis=None):
    # experiment1 = EisExperiment(potentiostat_address=potentiostat_address,
    #                             potentiostat_channel=potentiostat_channel,
    #                             vs_initial=vs_initial_eis,
    #                             vs_final=vs_final_eis,
    #                             Initial_frequency=100000,
    #                             Final_frequency=100)
    # experiment1.run_experiment(first=True, last=False)
    # p_data = experiment1.parsed_data
    # df = pd.DataFrame(p_data)
    # df.to_csv('C:\\Users\\Lab\\D3talesRobotics\\roboticsUI\\robotics_api\\workflows\\actions\\examples\\iR_testing\\eis_test4.csv')
    experiment2 = iRCompExperiment(amplitude_voltage=0.5, initial_frequency=500, final_frequency=5000,
                                   potentiostat_address=potentiostat_address,
                                   potentiostat_channel=potentiostat_channel)
    experiment2.run_experiment(first=True, last=False)
    scan_rate = 0.300
    collection_params = [{"voltage": 0., "scan_rate": scan_rate},
                         {"voltage": 0.7, "scan_rate": scan_rate},
                         {"voltage": -0.3, "scan_rate": scan_rate},
                         {"voltage": 0, "scan_rate": scan_rate}]
    ex_steps = [voltage_step(**p) for p in collection_params]

    exp = CvExperiment(ex_steps, potentiostat_address=potentiostat_address, potentiostat_channel=potentiostat_channel)
    exp.run_experiment(first=False, last=True)

    data = exp.data
    with open('examples/iR_testing/link_data.txt', 'a') as f:
        for data_step in data:
            current_values, data_info, data_record = data_step
            data_record_converted = []
            for i in data_record:
                try:
                    record = KBIO_api(ECLIB_DLL_PATH).ConvertNumericIntoSingle(i)
                except:
                    record = i
                data_record_converted.append(record)
            f.write(str(data_record_converted))
        f.write(" \n \n")
        f.close()
    # potentials = [s["Ewe"] for s in parsed_data]
    # current = [s["I"] for s in parsed_data]
    #
    # import matplotlib.pyplot as plt
    # plt.scatter(potentials, current)
    # plt.ylabel("Current")
    # plt.xlabel("Voltage")
    # plt.savefig("examples/iR_testing/cv_example.png")
    # exp.save_parsed_data("examples/iR_testing/cv_data_example.json")
    # exp.to_txt("examples/iR_testing/cv_example.csv")


def ca_exp(potentiostat_address=POTENTIOSTAT_A_ADDRESS, potentiostat_channel=2):
    experiment = CaExperiment(potentiostat_address=potentiostat_address, potentiostat_channel=potentiostat_channel)
    experiment.run_experiment(first=True, last=True)
    p_data = experiment.parsed_data
    df = pd.DataFrame(p_data)
    df.to_csv(
        r'C:\\Users\\Lab\\D3talesRobotics\\roboticsUI\\robotics_api\\workflows\\actions\\examples\\ca_testing\\ca_test6.csv')


if __name__ == "__main__":
    # ir_comp_ex(potentiostat_address=POTENTIOSTAT_A_ADDRESS, potentiostat_channel=2, vs_initial_eis=-1., vs_final_eis=1.)
    cv_ex(scan_rate=0.300)
    # ca_exp(potentiostat_address=POTENTIOSTAT_A_ADDRESS, potentiostat_channel=2)
