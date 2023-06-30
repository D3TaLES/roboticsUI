import sys
import time
import copy
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
    def __init__(self, nb_words, time_out=10, load_firm=True, cut_beginning=0, cut_end=0,
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

    def run_experiment(self):
        try:
            if not self.check_connection():
                self.id_, self.d_info = self.k_api.Connect(self.potent_address, self.time_out)  # Connect

            # Clear Data
            self.data = []

            # BL_LoadTechnique
            self.k_api.LoadTechnique(self.id_, self.potent_channel, self.tech_file, self.params, first=True, last=True,
                                     display=(VERBOSITY > 1))
            # BL_StartChannel
            self.k_api.StartChannel(self.id_, self.potent_channel)

            # experiment loop
            print("Start CV cycle...")
            while True:
                # BL_GetData
                data = self.k_api.GetData(self.id_, self.potent_channel)
                self.data.append(data)
                current_values, data_info, data_record = data

                if VERBOSITY:
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
            forward_idx = [i for i, _ in enumerate(voltages[:-1]) if voltages[i] > voltages[i+1]]
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
                 **kwargs):
        super().__init__(3, time_out=time_out, cut_beginning=cut_beginning, cut_end=cut_end, **kwargs)

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
                 **kwargs):
        super().__init__(6, time_out=time_out, cut_beginning=cut_beginning, cut_end=cut_end, **kwargs)

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


if __name__ == "__main__":
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
