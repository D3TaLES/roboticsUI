import sys
import time
import copy
import json
import datetime
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from dataclasses import dataclass
from scipy.stats import linregress

try:
    import _kbio.kbio_types as KBIO
    from _kbio.kbio_api import KBIO_api
    from _kbio.tech_types import TECH_ID
    from _kbio.kbio_tech import ECC_parm, make_ecc_parm, make_ecc_parms, print_experiment_data
except ModuleNotFoundError:
    warnings.warn("KBIO module not imported.")
from robotics_api.settings import *

VERBOSITY = 1
ECLIB_DLL_PATH = r"C:\EC-Lab Development Package\EC-Lab Development Package\\EClib64.dll"


@dataclass
class current_step:
    """Dataclass for representing a current step in an experiment."""
    current: float
    duration: float
    vs_init: bool = False


@dataclass
class voltage_step:
    """Dataclass for representing a voltage step in an experiment."""
    voltage: float
    scan_rate: float
    vs_init: bool = False


class PotentiostatExperiment:
    """Class for operating a BioLogic potentiostat during an electrochemistry experiment."""

    def __init__(self, nb_words, time_out=TIME_OUT, load_firm=True, cut_beginning=CUT_BEGINNING, cut_end=CUT_END,
                 run_iR=True, potentiostat_address=POTENTIOSTAT_A_ADDRESS, potentiostat_channel=1,
                 exe_path=ECLIB_DLL_PATH, **iR_kwargs):
        """Initializes the PotentiostatExperiment class.

        Args:
            nb_words (int): Number of rows for parsing.
            time_out (int): API connection timeout in seconds.
            load_firm (bool): If True, load firmware.
            cut_beginning (float): Percentage of the beginning of the data to cut off.
            cut_end (float): Percentage of the end of the data to cut off.
            run_iR (bool): If True, run iR compensation.
            potentiostat_address (str): Potentiostat connection address.
            potentiostat_channel (int): Potentiostat channel number.
            exe_path (str): Potentiostat executable path.
            **iR_kwargs: Keyword arguments for iR compensation settings.
        """
        self.nb_words = nb_words
        self.k_api = KBIO_api(exe_path)
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
        self.run_iR = run_iR
        self.ir_kwargs = iR_kwargs

    @staticmethod
    def normalize_steps(steps: list, data_class, min_steps=None):
        """Normalizes the experiment steps.

        Args:
            steps (list): List of steps for the experiment.
            data_class (type): Class type for the steps.
            min_steps (int, optional): Minimum number of steps to ensure.

        Returns:
            list: Normalized list of steps.
        """
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

    def run_iR_comp(self,
                    amplitude_voltage=0.5,  # Set this manually
                    final_frequency=5000,
                    initial_frequency=500,
                    average_n_times=5,
                    wait_for_steady=0,
                    sweep=True,
                    rcomp_level=RCOMP_LEVEL,
                    # rcmp_mode=0,  # always software unless an SP-300 series and running loop function
                    ):
         """Runs iR compensation before an experiment.

        Args:
            amplitude_voltage (float): Amplitude of the voltage.
            final_frequency (float): Final frequency for iR compensation.
            initial_frequency (float): Initial frequency for iR compensation.
            average_n_times (int): Number of times to average during iR compensation.
            wait_for_steady (float): Time to wait for the system to steady.
            sweep (bool): If True, perform a frequency sweep.
            rcomp_level (float): Level of resistance compensation.

        Returns:
            tuple: ECC parameters and technique file name for iR compensation.
        """
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
        """Checks the connection to the potentiostat.

        Returns:
            bool: True if connection is successful, False otherwise.
        """
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
        """Checks if the kernel is loaded for the potentiostat."""
        channel_info = self.k_api.GetChannelInfo(self.id_, self.potent_channel)
        if not channel_info.is_kernel_loaded:
            print("> kernel must be loaded in order to run the experiment")
            sys.exit(-1)

    def load_firmware(self):
        """Loads firmware for the potentiostat."""
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
        """Prints messages from the potentiostat during the experiment."""
        while True:
            msg = self.k_api.GetMessage(self.id_, self.potent_channel)
            if not msg:
                break
            print(msg)

    @property
    def tech_file(self):
        """Gets the technique file name for the experiment.

        Returns:
            str: Technique file name.
        """
        return ''

    def experiment_print(self, data_step):
        """Prints experiment data.

        Args:
            data_step (tuple): A tuple representing the experiment data step.
        """
        return None

    def run_experiment(self):
        """Runs the potentiostat experiment."""
        try:
            if not self.check_connection():
                self.id_, self.d_info = self.k_api.Connect(self.potent_address, self.time_out)  # Connect

            # Clear Data
            self.data = []

            # Perform iR compensation
            first = True
            if self.run_iR:
                ir_comp_params, ir_tech = self.run_iR_comp(**self.ir_kwargs)
                self.k_api.LoadTechnique(self.id_, self.potent_channel, ir_tech, ir_comp_params, first=first,
                                         last=False,
                                         display=(VERBOSITY > 1))
                first = False
                print("SUCCESS! iR compensation has been completed!")

            # BL_LoadTechnique
            print(self.id_)
            self.k_api.LoadTechnique(self.id_, self.potent_channel, self.tech_file, self.params, first=first, last=True,
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
                    self.experiment_print(exp_data)

                status = KBIO.PROG_STATE(current_values.State).name

                print("> old messages :")
                self.print_messages()
                if status == 'STOP':
                    break
                time.sleep(1)
            print("> experiment done")
        except KeyboardInterrupt:
            print(".. experiment interrupted")

        # BL_Disconnect
        self.k_api.Disconnect(self.id_)

    @property
    def parsed_data(self):
        """Parses the experiment data.

        Returns:
            list: Parsed experiment data.
        """
        return []

    @property
    def trimmed_data(self):
        """Trims the beginning and end of the experiment data.

        Returns:
            list: Trimmed experiment data.
        """
        extracted_data = self.parsed_data
        if not extracted_data:
            return []
        min_idx, max_idx = int(len(extracted_data) * self.cut_beginning), int(len(extracted_data) * (1 - self.cut_end))
        return extracted_data[min_idx:max_idx]

    def cv_row_parser(self, row):
        """Parses a row of cyclic voltammetry data.

        Args:
            row (list): Row of CV data.

        Returns:
            tuple: Parsed CV data row values.
        """
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
        return t, Freq, abs_Ewe, abs_Ece, abs_I, abs_Ice, i, i_range, phase_Zwe, phase_Zce, Ewe, Ece, abs_res, real_, imaginary_

    @property
    def iR_comp_data(self):
        """Parses and returns iR compensation data. All units in Ohm.

        Returns:
            tuple: Real and imaginary resistance in ohms.

        Raises:
            ValueError: If iR compensation was not run.
        """
        if self.run_iR:
            current_values, data_info, data_record = self.data[2]
            f, abs_Ewe, abs_I, phase_Zwe, ewe_raw, i_raw, _, \
                abs_Ece, abs_Ice, phase_Zce, ece_raw, _, _, t, i_range = data_record
            abs_Ewe = self.k_api.ConvertNumericIntoSingle(abs_Ewe)
            abs_I = self.k_api.ConvertNumericIntoSingle(abs_I)
            phase_Zwe = self.k_api.ConvertNumericIntoSingle(phase_Zwe)
            abs_res = abs_Ewe / abs_I
            real_ = abs_res * math.cos(phase_Zwe)
            imaginary_ = abs(abs_res * math.sin(phase_Zwe))
            return real_, imaginary_
        raise ValueError("iR compensation was not run, no value to return")

    def save_parsed_data(self, out_file):
        """Saves the parsed data to a JSON file.

        Args:
            out_file (str): File path to save the parsed data.
        """
        with open(out_file, 'w') as f:
            json.dump(self.parsed_data, f)

    def save_data_records(self, out_file):
        """Saves the data records to a file.

        Args:
            out_file (str): File path to save the data records.
        """
        data = self.data
        with open(out_file, 'w+') as f:
            for data_step in data:
                current_values, data_info, data_record = data_step
                data_record_converted = []
                for i in data_record:
                    try:
                        record = self.k_api.ConvertNumericIntoSingle(i)
                    except:
                        record = i
                    data_record_converted.append(record)
                f.write(str(data_record_converted))
            f.write(" \n \n")

    def to_txt(self, outfile, header='', note=''):
        """Saves the experiment data to a text file.

        Args:
            outfile (str): File path for the output text file.
            header (str, optional): Custom header for the output file.
            note (str, optional): Additional notes for the output file.
        """
        # Collect data
        extracted_data = self.trimmed_data
        if not extracted_data:
            print("WARNING. No CV data extracted.")
            return None
        times = [s["t"] for s in extracted_data]
        voltages = [s["Ewe"] for s in extracted_data]
        currents = [s["I"] for s in extracted_data]

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


class EisExperiment(PotentiostatExperiment):
    """
    Represents an Electrochemical Impedance Spectroscopy (EIS) experiment,
    inheriting from PotentiostatExperiment.

    This class is used to configure and run an EIS experiment with parameters
    such as initial and final voltage, frequency range, amplitude voltage,
    and other electrochemical settings. Data from the experiment is processed
    and stored in an internal list.

    Args:
        vs_initial (float, optional): Initial voltage of the experiment. Default is 0.
        vs_final (float, optional): Final voltage of the experiment. Default is 0.
        Initial_Voltage_step (float, optional): Step size for initial voltage. Default is 0.1.
        Final_Voltage_step (float, optional): Step size for final voltage. Default is 0.1.
        Duration_step (float, optional): Time duration for each step. Default is 0.5.
        Step_number (int, optional): Number of voltage steps. Default is 41.
        Record_every_dT (float, optional): Time interval for recording data. Default is 0.25.
        Record_every_dI (float, optional): Current interval for recording data. Default is 0.1.
        Final_frequency (float, optional): Final frequency in Hz for the EIS experiment. Default is 0.
        Initial_frequency (float, optional): Initial frequency in Hz for the EIS experiment. Default is 0.
        sweep (bool, optional): Whether to sweep between frequencies. Default is False.
        Amplitude_Voltage (float, optional): Amplitude of the voltage. Default is 0.01.
        Frequency_number (int, optional): Number of frequency points. Default is 10.
        Average_N_times (int, optional): Number of times to average the measurement. Default is 5.
        Correction (bool, optional): Apply correction to the data. Default is False.
        Wait_for_steady (float, optional): Time to wait for a steady state. Default is 0.1.
        **kwargs: Additional arguments passed to the parent class.

    Attributes:
        params (list): List of parameters for the EIS experiment.
        data (list): List to store the experimental data.
    """
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
        """
        Returns the appropriate technical file for the instrument family.

        Returns:
            str: The file name ('peis.ecc' or 'peis4.ecc') depending on whether
            the instrument is VMP3.
        """
        return 'peis.ecc' if self.is_VMP3 else 'peis4.ecc'

    def parameterize(self):
        """
        Creates and returns the experiment parameters by mapping experiment-specific
        attributes to ECC parameter objects.

        Returns:
            list: A list of ECC parameter objects, each corresponding to an experiment
            setting.
        """
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
        """
        Parses and extracts data from the experiment.

        Args:
            strict_error (bool, optional): If True, raises an error for unexpected record length. Default is False.

        Returns:
            list: A list of dictionaries, where each dictionary represents a data point
            with keys such as 't', 'Ewe', 'Ece', 'I', 'freq', and others.
        """
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
                t, Freq, abs_Ewe, abs_Ece, abs_I, abs_Ice, i, i_range, phase_Zwe, phase_Zce, \
                    Ewe, Ece, abs_res, real_, imaginary_ = self.cv_row_parser(row)

                extracted_data.append({'t': t, 'Ewe': Ewe, 'Ece': Ece, 'I': i, 'freq': Freq, 'abs_ewe': abs_Ewe,
                                       'abs_ece': abs_Ece, 'abs_iwe': abs_I, 'abs_ice': abs_Ice, 'i_range': i_range,
                                       'phase_zwe': phase_Zwe, 'phase_zce': phase_Zce, 'real_res': real_,
                                       'im_res': imaginary_})
                ix = inx

        return extracted_data

    def to_txt(self, outfile, header='', note=''):
        """
        Exports the parsed data to a CSV file.

        Args:
            outfile (str): The path to the output file.
            header (str, optional): Header text for the file. Default is an empty string.
            note (str, optional): Notes to be added to the file. Default is an empty string.
        """
        extracted_data = self.parsed_data
        df = pd.DataFrame(extracted_data)
        df.to_csv(outfile)

    def experiment_print(self, data_step):
        """
        Prints time, frequency, and real resistance for each data step.

        Args:
            data_step (tuple): A tuple containing current values, data info, and data record for each step.
        """
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
                abs_res = i / ewe
                real = abs_res * math.cos(phase_w)
                print('-------------------{} / {} / {}-------------------------'.format(t, freq, real))
            ix = inx


class CpExperiment(PotentiostatExperiment):
    """
    Class to run Chrono-Potentiometry (CP) experiments using a potentiostat.

    Chrono-Potentiometry is an electrochemical technique where the current is held constant, and the
    resulting potential is measured over time.

    Args:
        n_cycles (int): The number of cycles for the experiment. Must be an integer ≥ 0.
        record_every_dt (float): Time interval (in seconds) to record the data. Must be a float ≥ 0.
        record_every_de (float): Voltage interval (in volts) to record the data. Must be a float ≥ 0.
        i_range (str): Current range keyword defined by the _kbio library.
        repeat_count (int): Number of times to repeat the experiment.
        **kwargs: Additional keyword arguments passed to the parent class.

    Attributes:
        record_every_dt (float): Time interval (in seconds) to record the data.
        record_every_de (float): Voltage interval (in volts) to record the data.
        i_range (str): Current range keyword defined by the _kbio library.
        repeat_count (int): Number of times to repeat the experiment.
        n_cycles (int): The number of cycles for the experiment.
        params (list): List of parameter objects for the experiment configuration.
    """
    def __init__(self,
                 n_cycles=0,
                 record_every_dt=RECORD_EVERY_DT,  # seconds
                 record_every_de=CV_SAMPLE_INTERVAL,  # Volts
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
        """
        Returns the correct ECC file used by the potentiostat based on the instrument family.

        Returns:
            str: The ECC file path for the CP technique.
        """
        return "cp.ecc" if self.is_VMP3 else "cp4.ecc"

    def parameterize(self):
        """
        Defines and prepares the experiment parameters required for the potentiostat to run
        a Chrono-Potentiometry experiment. This includes setting the current step, duration, voltage,
        and recording intervals.

        Returns:
            list: A list of parameter objects required by the potentiostat.
        """
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
        """
        Parses the raw data collected during the experiment and extracts relevant information
        such as time, voltage (Ewe), current (I), and cycle number.

        Returns:
            list: A list of dictionaries containing the parsed data from the experiment.
        """
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
        """
        Prints a summary of one data step, showing the voltage (Ewe) values.

        Args:
            data_step (tuple): The current values, data information, and raw data for one step of the experiment.
        """
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
    Class to run Cyclic Voltammetry (CV) experiments using a potentiostat.

    Cyclic Voltammetry is an electrochemical technique in which the working electrode potential
    is cycled between two values while the resulting current is measured.

    Args:
        steps (list): List of step objects or nested lists defining voltage (V) and scan rate (mV/s) for each step.
        vs_initial (bool): Boolean indicating if the voltage is measured relative to the initial step.
        n_cycles (int): The number of cycles for the experiment. Must be an integer ≥ 0.
        scan_number (int): Number of scans in the experiment. Must be an integer ≥ 0.
        record_every_de (float): Voltage interval (in volts) to record data.
        average_over_de (bool): Whether to average the measurements over the voltage interval.
        min_steps (int): Minimum number of voltage steps for each cycle.
        **kwargs: Additional keyword arguments passed to the parent class.

    Attributes:
        steps (list): List of normalized step objects containing voltage and scan rate details.
        scan_number (int): Number of scans in the experiment.
        vs_initial (bool): Indicates if voltage is measured relative to the initial step.
        record_every_de (float): Voltage interval (in volts) to record data.
        average_over_de (bool): Boolean flag for averaging over the voltage interval.
        n_cycles (int): The number of cycles for the experiment.
        params (list): List of parameter objects for the experiment configuration.
    """
    def __init__(self,
                 steps: list,
                 vs_initial: bool = VS_INITIAL,
                 n_cycles: int = 0,
                 scan_number: int = 1,
                 record_every_de: float = CV_SAMPLE_INTERVAL,
                 average_over_de: bool = True,
                 min_steps: int = 6,
                 **kwargs):
        super().__init__(6, **kwargs)

        # Set Parameters
        self.steps = self.normalize_steps(steps, voltage_step, min_steps=min_steps)
        self.scan_number = scan_number
        self.vs_initial = vs_initial
        self.record_every_de = record_every_de
        self.average_over_de = average_over_de
        self.n_cycles = n_cycles

        self.params = self.parameterize()
        self.data = []

        # Set Parameters

    @property
    def tech_file(self):
        """
        Returns the correct ECC file used by the potentiostat based on the instrument family.

        Returns:
            str: The ECC file path for the CV technique.
        """
        return 'cv.ecc' if self.is_VMP3 else 'cv4.ecc'

    def parameterize(self):
        """
        Defines and prepares the experiment parameters required for the potentiostat to run
        a Cyclic Voltammetry experiment. This includes setting the voltage step, scan rate, and recording intervals.

        Returns:
            list: A list of parameter objects required by the potentiostat.
        """
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
        """
        Parses the raw data collected during the experiment and extracts relevant information
        such as time, voltage (Ewe), current (I), and cycle number.

        Returns:
            list: A list of dictionaries containing the parsed data from the experiment.
        """
        extracted_data = []
        data = self.data[3:] if self.run_iR else self.data
        for data_step in data:
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
        """
        Prints a summary of one data step, showing the voltage (Ewe) and current (I) values.

        Args:
            data_step (tuple): The current values, data information, and raw data for one step of the experiment.
        """
        current_values, data_info, data_record = data_step
        print("-------------------STEP-------------------")
        ix = 0
        for _ in range(1, data_info.NbRows):
            inx = ix + data_info.NbCols
            if self.is_VMP3:
                t_high, t_low, ec_raw, i_raw, ewe_raw, cycle = data_record[ix:inx]
            else:
                t_high, t_low, i_raw, ewe_raw, cycle = data_record[ix:inx]

            print("Volt:  {:02f} \t Current:  {:.2E}".format(self.k_api.ConvertNumericIntoSingle(ewe_raw),
                                                             self.k_api.ConvertNumericIntoSingle(i_raw)))

            ix = inx

    def plot(self, out_file):
        """
        Plots the current vs. voltage data from the experiment and saves the plot to a file.

        Args:
            out_file (str): The file path where the plot will be saved.
        """
        if not self.trimmed_data:
            print("Cannot plot data because there is no parsed_data. Make sure you have run an experiment.")
            return None
        potentials = [s["Ewe"] for s in self.trimmed_data]
        current = [s["I"] for s in self.trimmed_data]

        plt.scatter(potentials, current)
        plt.ylabel("Current")
        plt.xlabel("Voltage")
        plt.savefig(out_file)


class CaExperiment(PotentiostatExperiment):
    """
    Initializes a Chronoamperometry (CA) experiment setup.

    Args:
        steps (tuple): Sequence of voltage steps (V).
        vs_initial (tuple): Tuple indicating if the current step is relative to the initial step, bool.
        duration_step (float or list): Step duration in seconds (float). Can be a list for multiple steps.
        step_number (int): Number of voltage steps to perform.
        record_every_dt (float): Time interval for data recording (s).
        record_every_di (float): Current interval for data recording (A).
        n_cycles (int): Number of cycles to repeat the experiment.
        **kwargs: Additional arguments passed to the parent class.

    Attributes:
        steps (tuple): Sequence of voltage steps (V).
        vs_initial (tuple): Boolean flags for each step indicating whether it is relative to the initial step.
        duration (list): List of step durations in seconds.
        step_number (int): Number of voltage steps.
        record_every_dt (float): Time interval for data recording in seconds.
        record_every_di (float): Current interval for data recording.
        n_cycles (int): Number of cycles to repeat the experiment.
        params (list): List of experiment parameters.
        data (list): List to store recorded experiment data.
    """
    def __init__(self,
                 steps=(0.025, -0.025) * 50,
                 vs_initial=(True, False),
                 duration_step=(0.000024 * 100),
                 step_number=98,
                 record_every_dt=0.000024,
                 record_every_di=0.1,
                 n_cycles=2,
                 **kwargs):
        super().__init__(5, run_iR=False, **kwargs)

        # Set Parameters
        self.steps = steps
        self.vs_initial = vs_initial
        self.duration = duration_step if isinstance(duration_step, list) else [duration_step]
        self.step_number = step_number
        self.record_every_dt = record_every_dt
        self.record_every_di = record_every_di
        self.n_cycles = n_cycles

        self.params = self.parameterize()
        self.data = []

        # Set Parameters

    @property
    def tech_file(self):
        """
        Returns the correct ECC technique file based on the instrument family.

        Returns:
            str: ECC technique file name.
        """
        return 'ca.ecc' if self.is_VMP3 else 'ca4.ecc'

    def parameterize(self):
        """
        Parameterizes the CA experiment with the appropriate settings.

        Returns:
            list: List of experiment parameters for ECC technique.
        """
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
        """
        Extracts and parses the experimental data.

        Returns:
            list: List of dictionaries containing parsed data with keys 't' (time), 'Ewe' (working electrode potential),
                  'I' (current), and 'cycle' (cycle number).
        """
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
        """
        Prints a summary of the data step for the experiment.

        Args:
            data_step (tuple): Tuple containing current values, data info, and data records of a step.
        """
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



if __name__ == "__main__":
    def cp_ex():
        cp_steps = [
            current_step(0.001, 2),  # 1mA during 2s
            current_step(0.002, 1),  # 2mA during 1s
            current_step(0.0005, 3, True),  # 0.5mA delta during 3s
        ]
        cp_exp = CpExperiment(cp_steps)
        cp_exp.run_experiment()
        cp_exp.to_txt("cp_example.txt")


    def ca_exp(potentiostat_address=POTENTIOSTAT_A_ADDRESS, potentiostat_channel=2):
        experiment = CaExperiment(potentiostat_address=potentiostat_address, potentiostat_channel=potentiostat_channel)
        experiment.run_experiment()
        p_data = experiment.parsed_data
        df = pd.DataFrame(p_data)
        df.to_csv(os.path.join(TEST_DATA_DIR, "ca_testing\\ca_test6.csv"))


    def cv_ex(scan_rate=0.100, potentiostat_channel=1, **kwargs):
        collection_params = [{"voltage": 0., "scan_rate": scan_rate},
                             {"voltage": 0, "scan_rate": scan_rate},
                             {"voltage": 0., "scan_rate": scan_rate}]
        ex_steps = [voltage_step(**p) for p in collection_params]
        exp = CvExperiment(ex_steps, potentiostat_channel=potentiostat_channel, **kwargs)
        exp.run_experiment()
        exp.to_txt(f"{TEST_DATA_DIR}/cv_ex_ch{potentiostat_channel}.csv")
        exp.plot(f"{TEST_DATA_DIR}/cv_ex_ch{potentiostat_channel}.png")
        print(exp.iR_comp_data)
        # exp.save_data_records(f"{TEST_DATA_DIR}/cv_ex_ch{potentiostat_channel}.txt")
        # exp.save_parsed_data(f"{TEST_DATA_DIR}/cv_ex_ch{potentiostat_channel}.json")


    # ca_exp(potentiostat_address=POTENTIOSTAT_A_ADDRESS, potentiostat_channel=2)
    cv_ex(potentiostat_channel=1, scan_rate=0.100, run_iR=True)
