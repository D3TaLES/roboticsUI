# using sphinx

version=0.2
author='Duke, Rebekah'
projectname='D<sup>3</sup>TaLES Robotics UI'

MKDOCS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd $MKDOCS_DIR
cd ../../
rm -rf docs doc
mkdir docs
export DB_INFO_FILE=$PWD/db_info_ex.json

cat -H "$projectname" -A "$author" -V $version --full -o ./doc ./roboticsUI
sphinx-apidoc -H "$projectname" -A "$author" -V $version --full -o ./doc ./roboticsUI
cp $MKDOCS_DIR/conf.py ./doc/
cp $MKDOCS_DIR/index.rst ./doc/
cp $MKDOCS_DIR/*.md ./doc/
cp $MKDOCS_DIR/*.png ./doc/

cd doc
make clean
make html
pwd

mv _build/html/* ../docs
cd ../
rm -rf doc
touch docs/.nojekyll
cd $MKDOCS_DIR


