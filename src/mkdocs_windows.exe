# using sphinx

$env:version=0.2
$env:author='Duke, Rebekah'
$env:projectname='D<sup>3</sup>TaLES Robotics UI'
$env:MKDOCS_DIR="C:\Users\Lab\D3talesRobotics\roboticsUI\docs_src"

cd $env:MKDOCS_DIR
cd ../
rm -r docs/
mkdir $env:MKDOCS_DIR/_temp

sphinx-apidoc -H "$env:projectname" -A "$env:author" -V $env:version --full -o $env:MKDOCS_DIR/_temp ./robotics_api
cp $env:MKDOCS_DIR/conf.py $env:MKDOCS_DIR/_temp
cp $env:MKDOCS_DIR/index.rst $env:MKDOCS_DIR/_temp
cp $env:MKDOCS_DIR/*.md $env:MKDOCS_DIR/_temp
cp $env:MKDOCS_DIR/*.png $env:MKDOCS_DIR/_temp

cd $env:MKDOCS_DIR/_temp
make clean
make html

mkdir docs
cp -r
touch _build/html/.nojekyll
cd $env:MKDOCS_DIR


