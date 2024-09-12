export BASE_DIR="/mnt/e/research/D3TaLES/robotics/roboticsUI"

cd $BASE_DIR
rm -r docs/ _temp/
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
touch $BASE_DIR/docs/.
rm -r  $BASE_DIR/_temp/
cd $BASE_DIR


