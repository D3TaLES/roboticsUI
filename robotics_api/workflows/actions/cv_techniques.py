import sys
import time
import copy
import json

import pandas as pd
import pint
import warnings
import datetime
import numpy as np
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
    def __init__(self, nb_words, time_out=10, load_firm=True, cut_beginning=0, cut_end=0):
        self.nb_words = nb_words  # number of rows for parsing
        self.k_api = KBIO_api(ECLIB_DLL_PATH)
        self.id_, self.d_info = self.k_api.Connect(POTENTIOSTAT_ADDRESS, time_out)
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

    def check_connection(self):
        conn = self.k_api.TestConnection(self.id_)
        if not conn:
            print(f"> device[{POTENTIOSTAT_ADDRESS}] must be connected to run the experiment")
            return False
        # BL_GetChannelInfos
        channel_info = self.k_api.GetChannelInfo(self.id_, POTENTIOSTAT_CHANNEL)
        # BL_LoadFirmware
        if channel_info.has_no_firmware and self.load_firm:
            print("No firmware loaded.")
            self.load_firmware()
        return True

    def check_kernel(self):
        # BL_GetChannelInfos
        channel_info = self.k_api.GetChannelInfo(self.id_, POTENTIOSTAT_CHANNEL)
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
        channel_map = self.k_api.channel_map({POTENTIOSTAT_CHANNEL})
        # BL_LoadFirmware
        self.k_api.LoadFirmware(self.id_, channel_map, firmware=firmware_path, fpga=fpga_path, force=True)

    def print_messages(self):
        while True:
            msg = self.k_api.GetMessage(self.id_, POTENTIOSTAT_CHANNEL)
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
                self.id_, self.d_info = self.k_api.Connect(POTENTIOSTAT_ADDRESS, self.time_out)  # Connect

            # Clear Data
            self.data = []

            # BL_LoadTechnique
            self.k_api.LoadTechnique(self.id_, POTENTIOSTAT_CHANNEL, self.tech_file, self.params, first=True, last=True,
                                     display=(VERBOSITY > 1))
            # BL_StartChannel
            self.k_api.StartChannel(self.id_, POTENTIOSTAT_CHANNEL)

            # experiment loop
            print("Start {} cycle...".format(self.tech_file[:-4]))
            while True:
                # BL_GetData
                data = self.k_api.GetData(self.id_, POTENTIOSTAT_CHANNEL)
                self.data.append(data)
                print(data)
                current_values, data_info, data_record = data

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

        with open(outfile, 'w') as fn:
            fn.write(datetime.datetime.now().strftime("%c") + "\n")
            fn.write("Cyclic Voltammetry\n")
            fn.write("File: {}\n".format(outfile))
            fn.write("Data Source: KBIO Potentiostat\n")
            fn.write("Instrument Model: {}\n".format(self.d_info.model))
            fn.write("Header: {}\n".format(header))
            fn.write("Note: {}\n\n".format(note))
            fn.write("Init E (V) = {:.2f}\n".format(voltages[0]))
            fn.write("High E (V) = {:.2f}\n".format(max(voltages)))
            fn.write("Low E (V) = {:.2f}\n".format(min(voltages)))
            # fn.write("Init P/N = {}\n".format(''))
            fn.write("Scan Rate (V/s) = {:.3f}\n".format(float(self.scan_rate)))
            fn.write("Segment = {}\n".format(len(self.steps)))
            fn.write("Sample Interval (V) = {:.3e}\n".format(self.record_every_de or np.average(np.diff(voltages))))
            # fn.write("Quiet Time (sec) = {}\n".format(''))
            # fn.write("Sensitivity (A/V) = {}\n".format(''))
            fn.write("\n")
            fn.write("Potential/V, Current/A\n")
            fn.writelines(["{:.3e}, {:.3e}\n".format(v, i) for v, i in zip(voltages, currents)])


class iRCompExperiment(PotentiostatExperiment):
    # TODO documentation
    def __init__(self,
                 amplitude_voltage=0.5,  # Set this manually
                 final_frequency=FINAL_FREQUENCY,  # TODO this
                 initial_frequency=INITIAL_FREQUENCY,  # TODO this
                 average_n_times=5,  # TODO Find best N of times
                 wait_for_steady=0,  # TODO what does this mean
                 sweep=True,
                 rcomp_level=RCOMP_LEVEL,
                 rcmp_mode=0,  # always software unless an SP-300 series and running loop function
                 time_out=TIME_OUT,
                 load_firm=True):
        super().__init__(15, time_out=time_out, load_firm=load_firm, cut_beginning=0, cut_end=0)

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
                freq, abs_Ewe, abs_I, phase_Zwe, ewe_raw, i_raw, _, \
                    abs_Ece, abs_Ice, phase_Zce, ece_raw, _, _, t, i_range = row

                # compute timestamp in seconds
                t = self.k_api.ConvertNumericIntoSingle(t)
                # Ewe and current as floats
                Freq = self.k_api.ConvertNumericIntoSingle(freq)
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

                extracted_data.append({'t': t, 'Ewe': Ewe, 'Ece': Ece, 'I': i, 'freq': Freq, 'abs_ewe': abs_Ewe,
                                       'abs_ece': abs_Ece, 'abs_iwe': abs_I, 'abs_ice': abs_Ice, 'i_range': i_range,
                                       'phase_zwe': phase_Zwe, 'phase_zce': phase_Zce})
                ix = inx

        return extracted_data

    def to_txt(self, outfile, header='', note=''):
        extracted_data = self.parsed_data
        df = pd.DataFrame(extracted_data)
        df.to_csv(outfile)

    def experiment_print(self, data_info, data_record):
        # TODO CHANGE
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


class CpExperiment(PotentiostatExperiment):
    """
    Class to run Chrono-Potentiometry technique experiments
        :param steps : list of lists OR current_step objects: current (A), duration (s), vs_init (bool, default False)
        :param n_cycles : Number of cycle, integer ≥ 0
        :param record_every_dt : recording on dt (s), float ≥ 0
        :param record_every_de : recording on dE (V), float ≥ 0
        :param i_range : kbio I_RANGE keyword, str
        :param time_out : time to wait, float
    """

    def __init__(self,
                 steps: list,  # list of lists OR current_step objects: current, duration, vs_init
                 n_cycles=N_CYCLES,
                 record_every_dt=RECORD_EVERY_DT,  # seconds
                 record_every_de=RECORD_EVERY_DE,  # Volts
                 i_range=I_RANGE,
                 cut_beginning=CUT_BEGINNING,
                 cut_end=CUT_END,
                 time_out=TIME_OUT,
                 min_steps=None,
                 load_firm=True):
        super().__init__(3, time_out=time_out, load_firm=load_firm, cut_beginning=cut_beginning, cut_end=cut_end)

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

    def experiment_print(self, data_info, data_record):
        print("-------------------VOLTAGE-------------------------")
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
                 cut_beginning=CUT_BEGINNING,
                 cut_end=CUT_END,
                 time_out=TIME_OUT,
                 min_steps=MIN_CV_STEPS,
                 rcomp_level=RCOMP_LEVEL,
                 load_firm=True):
        super().__init__(6, time_out=time_out, load_firm=load_firm, cut_beginning=cut_beginning, cut_end=cut_end)

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
                t_high, t_low, ec_raw, i_raw, ewe_raw, cycle = row

                # compute timestamp in seconds
                t = current_values.TimeBase * (t_high << 32) + t_low
                # Ewe and current as floats
                Ewe = self.k_api.ConvertNumericIntoSingle(ewe_raw)
                Ec = self.k_api.ConvertNumericIntoSingle(ec_raw)
                i = self.k_api.ConvertNumericIntoSingle(i_raw)

                extracted_data.append({'t': t, 'Ewe': Ewe, 'Ec': Ec, 'I': i, 'cycle': cycle})
                ix = inx
        return extracted_data


def cp_ex():
    cp_steps = [
        current_step(0.001, 2),  # 1mA during 2s
        current_step(0.002, 1),  # 2mA during 1s
        current_step(0.0005, 3, True),  # 0.5mA delta during 3s
    ]
    cp_exp = CpExperiment(cp_steps)
    cp_exp.run_experiment()
    cp_exp.to_txt("cp_example.txt")


def cv_ex():
    SCAN_RATE = 0.500  # V/s
    collection_params = [{"voltage": 0., "scan_rate": SCAN_RATE},
                         {"voltage": 0.8, "scan_rate": SCAN_RATE},
                         {"voltage": 0, "scan_rate": SCAN_RATE}]
    ex_steps = [voltage_step(**p) for p in collection_params]
    experiment = CvExperiment(ex_steps)
    print(experiment.steps)
    # experiment.parameterize()
    experiment.run_experiment()
    parsed_data = experiment.parsed_data

    potentials = [s["Ewe"] for s in parsed_data]
    current = [s["I"] for s in parsed_data]
    import matplotlib.pyplot as plt

    plt.scatter(potentials, current)
    plt.ylabel("Current")
    plt.xlabel("Voltage")
    plt.savefig("examples/cv_example.png")
    try:
        experiment.to_txt("examples/cv_example.csv")
    except:
        experiment.to_txt("examples/cv_example_backup.csv")

if __name__ == "__main__":
    data = []
    # for i in range(INITIAL_FREQUENCY, FINAL_FREQUENCY, 5):
    for i in [0.1, 0.2, 0.5, 0.7, 1, 2.5, 5, 7.5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 70, 80, 90, 100, 125, 150, 175, 200, 250, 300, 350, 400, 450, 500, 600, 700, 800, 900, 1000, 1250, 1500, 1750, 2000, 2500, 3000]:
        experiment = iRCompExperiment(amplitude_voltage=0.5, initial_frequency=i)
        experiment.run_experiment()
        parsed_data = experiment.parsed_data
        print(parsed_data)
        data.append(parsed_data)
    with open(r'C:/Users/Lab/D3talesRobotics/roboticsUI/robotics_api/workflows/actions/examples/iR_testing/iR_freq_test_2.JSON', "w") as f:
        json.dump(data, f)
