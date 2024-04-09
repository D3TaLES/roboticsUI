import hardpotato as hp
import softpotato as sp
from robotics_api.settings import *
from d3tales_api.Processors.parser_cv import *


# Initialization:
pot_model = POTENTIOSTAT_B_EXE_PATH.split("\\")[-1].split(".")[0]
hp.potentiostat.Setup(pot_model, POTENTIOSTAT_B_EXE_PATH, TEST_DATA_DIR, port=POTENTIOSTAT_A_ADDRESS)


def cv_ex(resistance=0):
    # Experimental parameters:
    Eini = 0  # V, initial potential
    Ev1 = 0  # V, first vertex potential
    Ev2 = 0.8  # V, second vertex potential
    Efin = 0  # V, final potential
    sr = 0.01  # V/s, scan rate
    dE = 0.001  # V, potential increment
    nSweeps = 1  # number of sweeps
    sens = 1e-2  # A/V, current sensitivity
    fileName = 'CV'  # base file name for data file
    header = 'CV'  # header for data file

    # Initialize experiment:
    cv = hp.potentiostat.CV(Eini, Ev1, Ev2, Efin, sr, dE, nSweeps, sens, fileName, header, resistance=resistance)
    # Run experiment:
    cv.run()

    # Load recently acquired data
    data = hp.load_data.CV(fileName + '.txt', out_folder, pot_model)
    i = data.i
    E = data.E

    # Plot CV with softpotato
    sp.plotting.plot(E, i, fig=1, show=1)


def ircomp_ex():
    # Experimental parameters:
    Eini = 0  # V, initial potential
    low_freq = 10000  # Hz, low frequency
    high_freq = 100000  # Hz, high frequency
    amplitude = 0.01  # V, ac amplitude (half peak-to-peak)
    sens = 1e-5  # A/V, current sensitivity
    fileName = 'iRComp'  # base file name for data file
    header = 'iRComp'  # header for data file

    eis = hp.potentiostat.EIS(Eini, low_freq, high_freq, amplitude, sens, fileName, header)
    eis.run()

    data = ParseChiESI(os.path.join(out_folder, fileName+".txt"))
    return data.resistance


def ca_ex():
    # Experimental parameters. (None means use robotics default)
    Eini = 0  # V, initial potential
    Ev1 = 0.025  # V, first vertex potential
    Ev2 = -0.025  # V, second vertex potential
    pw = None  # 1e-4  # s, pulse width
    dE = None  # 1e-6  # V, potential increment
    nSweeps = None  # 200  # number of sweeps
    sens = None  # 1e-4  # A/V, current sensitivity
    fileName = 'CA'  # base file name for data file
    header = 'CA'  # header for data file

    ca = hp.potentiostat.CA(Eini, Ev1, Ev2,
                            dE or RECORD_EVERY_DE,
                            nSweeps or STEPS,
                            pw or PULSE_WIDTH,
                            sens or SENSITIVITY,
                            fileName=fileName, header=header)
    ca.run()

    # Load recently acquired data
    data = ParseChiCA(os.path.join(out_folder, fileName+".txt"))
    print(data.parsed_data.measured_resistance)

    # Plot CV with softpotato
    # sp.plotting.plot(data.t, data.i, xlab='$t$ / s', fig=1, show=1)


if __name__ == "__main__":
    # resist = ircomp_ex()
    # print(resist)
    # cv_ex(resistance=resist)
    ca_ex()
