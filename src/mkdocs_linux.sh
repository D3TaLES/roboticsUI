export BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH=$BASE_DIR

cd $BASE_DIR
rm -rf docs/ _temp/
mkdir $BASE_DIR/_temp
mkdir $BASE_DIR/docs

sphinx-apidoc --full -o $BASE_DIR/_temp $BASE_DIR/robotics_api
cp $BASE_DIR/src/conf.py $BASE_DIR/_temp/
cp $BASE_DIR/src/index.rst $BASE_DIR/_temp/
cp $BASE_DIR/src/*.md $BASE_DIR/_temp/
cp -r $BASE_DIR/src/media $BASE_DIR/_temp/


cd $BASE_DIR/_temp
make clean
make html

cp -r $BASE_DIR/_temp/_build/html/* $BASE_DIR/docs
cp $BASE_DIR/src/.nojekyll $BASE_DIR/docs/
rm -rf  $BASE_DIR/_temp/
cd $BASE_DIR


