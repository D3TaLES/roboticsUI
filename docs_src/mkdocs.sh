# using sphinx

$env:version=0.2
$env:author='Duke, Rebekah'
$env:projectname='D<sup>3</sup>TaLES Robotics UI'
$env:MKDOCS_DIR="C:\Users\Lab\D3talesRobotics\roboticsUI\docs_src"

cd $env:MKDOCS_DIR
cd ../
rm -r docs/

sphinx-apidoc -H "$env:projectname" -A "$env:author" -V $env:version --full -o ./docs ./robotics_api
cp $env:MKDOCS_DIR/conf.py docs/
cp $env:MKDOCS_DIR/index.rst ./docs/
cp $env:MKDOCS_DIR/*.md ./docs/
cp $env:MKDOCS_DIR/*.png ./docs/

cd docs/
make clean
make html

touch _build/html/.nojekyll
cd $env:MKDOCS_DIR


