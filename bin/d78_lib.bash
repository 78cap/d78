function run_distro_cmd() {
  BASE_DIR=$HOME/work/d78
  CLEAN_SRC_DIR=${BASE_DIR:?not set}/bin/.repo/sec
  SRC_DIR=$HOME/work/sec
  DISTRO_DIR=$CLEAN_SRC_DIR/gradleBuild/${PROJECT_NAME:?not set}/distributions/$PROJECT_NAME-distro
  #DISTRO_DIR=${BASE_DIR:?not set}/bin/.repo/distros/$PROJECT_NAME-distro

  if [ "$1" == "--update" ]; then
    shift
    [ -d $DISTRO_DIR ] && rm -r $DISTRO_DIR
    [ $? != 0 ] && echo "Error occurred" && exit 1
    DISTRO_CMD=""
  fi
  if [ ! -e $DISTRO_DIR/venv/requirements.txt ]; then
    echo "Updating  $PROJECT_NAME distro in $DISTRO_DIR..."
    hg --cwd $SRC_DIR archive -r @ -t files $CLEAN_SRC_DIR -I settings.gradle -I gradle -I gradlew -I publics && \
    cd $CLEAN_SRC_DIR && \
    ./gradlew xargs-$PROJECT_NAME-distro --cmd "[distro_dir]/bin/post-install" && \
    echo "Done updating $DISTRO_DIR."
  fi
  export PATH=$DISTRO_DIR/bin:$PATH
  [ ! -z "$DISTRO_CMD" ] && exec $DISTRO_CMD "$@"
}