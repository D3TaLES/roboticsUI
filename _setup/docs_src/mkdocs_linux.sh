export BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH=$BASE_DIR
cd $BASE_DIR
git pull

rm -rf _temp/ docs/
mkdir $BASE_DIR/_temp
mkdir $BASE_DIR/docs


sphinx-apidoc --full -o $BASE_DIR/_temp $BASE_DIR/robotics_api
cp $BASE_DIR/_setup/docs_src/conf.py $BASE_DIR/_temp/
cp $BASE_DIR/_setup/docs_src/index.rst $BASE_DIR/_temp/
cp $BASE_DIR/_setup/docs_src/*.md $BASE_DIR/_temp/
cp -r $BASE_DIR/_setup/docs_src/media $BASE_DIR/_temp/
cp -r $BASE_DIR/_setup/docs_src/_static/* $BASE_DIR/_temp/_static

cd $BASE_DIR/_temp
make.bat clean
make.bat html

cd $BASE_DIR
cp -r $BASE_DIR/_temp/_build/html/* $BASE_DIR/docs
touch $BASE_DIR/docs/.nojekyll
rm -rf  $BASE_DIR/_temp/

git add docs/
git commit -am "Update documentation" || echo "No changes to commit"
git push
