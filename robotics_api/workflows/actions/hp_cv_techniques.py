import hardpotato as hp
import softpotato as sp
from robotics_api.standard_variables import *


# Folder where to save the data, it needs to be created previously
out_folder = "/examples"

# Initialization:
hp.potentiostat.Setup(CHI_MODEL, CHI_EXE_PATH, out_folder)


def cv_ex():
    # Experimental parameters:
    Eini = -0.5     # V, initial potential
    Ev1 = 0.5       # V, first vertex potential
    Ev2 = -0.5      # V, second vertex potential
    Efin = -0.5     # V, final potential
    sr = 1          # V/s, scan rate
    dE = 0.001      # V, potential increment
    nSweeps = 2     # number of sweeps
    sens = 1e-6     # A/V, current sensitivity
    fileName = 'CV' # base file name for data file
    header = 'CV'   # header for data file

    # Initialize experiment:
    cv = hp.potentiostat.CV(Eini, Ev1, Ev2, Efin, sr, dE, nSweeps, sens, fileName, header)
    # Run experiment:
    cv.run()

    # Load recently acquired data
    data = hp.load_data.CV(fileName +'.txt', out_folder, CHI_MODEL)
    i = data.i
    E = data.E

    # Plot CV with softpotato
    sp.plotting.plot(E, i, fig=1, show=1)


if __name__=="__main__":
    cv_ex()