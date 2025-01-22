# Welcome to Macro Command!
#
# Use this dialog box to execute a series of commands.
# This is analogous to batch files in Windows or shell scripts in Unix/Linux.
# Click the 'Help' button for more information.
# -------------------------

# Beep three times.
for: 3       ; comments following ';' are also ignored
  beep
  delay: 1
next         # end of 'for...next' loop

# Run a CV with internal dummy cell (resistor).
dummyon      # Control > Cell > Test with Internal Dummy Cell
tech: cv
ei: 0.1
eh: 0.1
el: -0.1
qt: 0        # Quiet Time
run
dummyoff
