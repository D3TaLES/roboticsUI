import hardpotato as hp
import softpotato as sp
from robotics_api.settings import *
from d3tales_api.Processors.parser_echem import *


# Initialization:
pot_model = POTENTIOSTAT_B_EXE_PATH.split("\\")[-1].split(".")[0]
hp.potentiostat.Setup(pot_model, POTENTIOSTAT_B_EXE_PATH, TEST_DATA_DIR, port=POTENTIOSTAT_B_ADDRESS)


def cv_ex(resistance=0):
    # Experimental parameters:
    Eini = 0  # V, initial potential
    Ev1 = 0  # V, first vertex potential
    Ev2 = 0.8  # V, second vertex potential
    Efin = 0  # V, final potential
    sr = 0.1  # V/s, scan rate
    dE = None  # V, potential increment
    nSweeps = None  # number of sweeps
    sens = None  # A/V, current sensitivity
    fileName = 'CV'  # base file name for data file
    header = 'CV'  # header for data file

    # Initialize experiment:
    cv = hp.potentiostat.CV(Eini=Eini, Ev1=Ev1, Ev2=Ev2, Efin=Efin, sr=sr, resistance=resistance,
                            dE=dE or CV_SAMPLE_INTERVAL,
                            nSweeps=nSweeps or CA_STEPS,
                            sens=sens or CV_SENSITIVITY,
                            fileName=fileName, header=header)
    # Run experiment:
    cv.run()

    # Load recently acquired data
    data = hp.load_data.CV(fileName + '.txt', TEST_DATA_DIR, pot_model)
    i = data.i
    E = data.E

    # Plot CV with softpotato
    sp.plotting.plot(E, i, fig=1, show=1)


def ircomp_ex():
    # Experimental parameters:
    Eini = 0  # V, initial potential
    low_freq = None  # Hz, low frequency
    high_freq = None  # Hz, high frequency
    amplitude = None  # V, ac amplitude (half peak-to-peak)
    sens = None  # A/V, current sensitivity
    fileName = 'iRComp'  # base file name for data file
    header = 'iRComp'  # header for data file

    eis = hp.potentiostat.EIS(Eini=Eini,
                              low_freq=low_freq or INITIAL_FREQUENCY, high_freq=high_freq or FINAL_FREQUENCY,
                              amplitude=amplitude or AMPLITUDE,
                              sens=sens or CV_SENSITIVITY,
                              fileName=fileName, header=header)
    eis.run()

    data = ProcessChiESI(os.path.join(TEST_DATA_DIR, fileName+".txt"))
    return data.resistance


def ca_ex():
    # Experimental parameters. (None means use robotics default)
    Eini = 0  # V, initial potential
    Ev1 = 0.025  # V, first vertex potential
    Ev2 = -0.025  # V, second vertex potential
    pw = None  # 1e-4  # s, pulse width
    si = None  # 1e-6  # V, potential increment
    nSweeps = None  # 200  # number of sweeps
    sens = None  # 1e-4  # A/V, current sensitivity
    fileName = 'CA'  # base file name for data file
    header = 'CA'  # header for data file

    ca = hp.potentiostat.CA(Eini=Eini, Ev1=Ev1, Ev2=Ev2,
                            dE=si or CA_SAMPLE_INTERVAL,
                            nSweeps=nSweeps or CA_STEPS,
                            pw=pw or CA_PULSE_WIDTH,
                            sens=sens or CA_SENSITIVITY,
                            fileName=fileName, header=header)
    ca.run()

    # Load recently acquired data
    data = ProcessChiCA(os.path.join(TEST_DATA_DIR, fileName+".txt"))
    print("Resistance (Ohm): ", data.measured_resistance)

    # Plot CV with softpotato
    # sp.plotting.plot(data.t, data.i, xlab='$t$ / s', fig=1, show=1)


if __name__ == "__main__":
    # resist = ircomp_ex()
    # print(resist)
    # cv_ex(resistance=resist)
    ca_ex()
