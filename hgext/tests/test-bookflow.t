
#
# To run the test get the mercurial distro and run:
# <repo_path>/tests/run-tests.py test-bookflow.t
#
initialize
  $ alias hgg="hg --config extensions.bookflow=`dirname $TESTDIR`/bookflow.py"
  $ make_changes() { d=`pwd`; [ ! -z $1 ] && cd $1; echo "test $(basename `pwd`)" >> test; hgg commit -Am"${2:-test}"; r=$?; cd $d; return $r; }
  $ assert_clean() { ls -1 $1 | grep -v "test$" | cat;}
  $ ls -1a
  .
  ..
  $ hg init a
  $ cd a
  $ echo 'test' > test; hg commit -Am'test'
  adding test

clone to b

  $ mkdir ../b
  $ cd ../b
  $ hg clone ../a .
  updating to branch default
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hgg branch X
  abort: Branching should be done using bookmarks:
  hg bookmark X
  [255]
  $ hgg bookmark X
  $ hgg bookmarks
  * X                         0:* (glob)
  $ make_changes
  $ hgg push ../a > /dev/null

  $ hg bookmarks
   \* X                         1:* (glob)

change a
  $ cd ../a
  $ hgg up
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ echo 'test' >> test; hg commit -Am'test'


pull in b
  $ cd ../b
  $ hgg pull -u
  pulling from $TESTTMP/a
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files
  new changesets * (glob)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (leaving bookmark X)
  $ assert_clean
  $ hg bookmarks
     X                         1:* (glob)

check protection of @ bookmark
  $ hgg bookmark @
  $ hgg bookmarks
   \* @                         2:* (glob)
     X                         1:* (glob)
  $ make_changes
  abort: Can't commit, bookmark @ is protected
  [255]

  $ assert_clean
  $ hgg bookmarks
   \* @                         2:* (glob)
     X                         1:* (glob)

  $ hgg --config bookflow.protect= commit  -Am"Updated test"

  $ hgg bookmarks
   \* @                         3:* (glob)
     X                         1:* (glob)

check requirement for an active bookmark
  $ hgg bookmark -i
  $ hgg bookmarks
     @                         3:* (glob)
     X                         1:* (glob)
  $ make_changes
  abort: Can't commit without an active bookmark
  [255]
  $ hgg revert test
  $ rm test.orig
  $ assert_clean


make the bookmark move by updating it on a, and then pulling
# add a commit to a
  $ cd ../a
  $ hg bookmark X
  $ hgg bookmarks
   \* X                         2:* (glob)
  $ make_changes
  $ hgg bookmarks
   * X                         3:81af7977fdb9

# go back to b, and check out X
  $ cd ../b
  $ hgg up X
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (activating bookmark X)
  $ hgg bookmarks
     @                         3:* (glob)
   \* X                         1:* (glob)

# pull, this should move the bookmark forward, because it was changed remotely
  $ hgg pull -u | grep "updating to active bookmark X"
  updating to active bookmark X

  $ hgg bookmarks
     @                         3:* (glob)
   * X                         4:81af7977fdb9

the bookmark should not move if it diverged from remote
## assumes we're still on bookmark X
  $ assert_clean ../a
  $ assert_clean ../b
  $ make_changes ../a
  $ make_changes ../b
  $ assert_clean ../a
  $ assert_clean ../b
  $ hgg --cwd ../a bookmarks
   * X                         4:238292f60a57
  $ hgg --cwd ../b bookmarks
     @                         3:* (glob)
   * X                         5:096f7e86892d
  $ cd ../b
  $ # make sure we can't push after bookmarks diverged
  $ hgg push -B X | grep abort
  abort: push creates new remote head * with bookmark 'X'! (glob)
  (pull and merge or see 'hg help push' for details about pushing new heads)
  [1]
  $ hgg pull -u | grep divergent
  divergent bookmark X stored as X@default
  1 other divergent bookmarks for "X"
  $ hgg bookmarks
     @                         3:* (glob)
   * X                         5:096f7e86892d
     X@default                 6:238292f60a57
  $ hgg id -in
  096f7e86892d 5
  $ make_changes
  $ assert_clean
  $ hgg bookmarks
     @                         3:* (glob)
   * X                         7:227f941aeb07
     X@default                 6:238292f60a57

now merge with the remote bookmark
  $ hgg merge X@default --tool :local > /dev/null
  $ assert_clean
  $ hgg commit -m"Merged with X@default"
  $ hgg bookmarks
     @                         3:* (glob)
   * X                         8:26fed9bb3219
  $ hgg push -B X | grep bookmark
  pushing to $TESTTMP/a (?)
  updating bookmark X
  $ cd ../a
  $ hgg up > /dev/null
  $ hgg bookmarks
   * X                         7:26fed9bb3219

test hg pull when there is more than one descendant
  $ cd ../a
  $ hgg bookmark Z
  $ hgg bookmark Y
  $ make_changes . YY
  $ hgg up Z > /dev/null
  $ make_changes . ZZ
  created new head
  $ hgg bookmarks
     X                         7:26fed9bb3219
     Y                         8:131e663dbd2a
   * Z                         9:b74a4149df25
  $ hg log -r 'p1(Y)' -r 'p1(Z)' -T '{rev}\n' # prove that Y and Z share the same parent
  7
  $ hgg log -r 'Y%Z' -T '{rev}\n'  # revs in Y but not in Z
  8
  $ hgg log -r 'Z%Y' -T '{rev}\n'  # revs in Z but not in Y
  9
  $ cd ../b
  $ hgg pull -u > /dev/null
  $ hgg id
  b74a4149df25 tip Z
  $ hgg bookmarks | grep \*  # no active bookmark
  [1]



test shelving
  $ cd ../a
  $ echo anotherfile > anotherfile # this change should not conflict
  $ hgg add anotherfile
  $ hgg commit -m"Change in a"
  $ cd ../b
  $ hgg up Z | grep Z
  (activating bookmark Z)
  $ hgg book | grep \* # make sure active bookmark
   \* Z                         10:* (glob)
  $ echo "test b" >> test
  $ hgg diff --stat
   test |  1 +
   1 files changed, 1 insertions(+), 0 deletions(-)
  $ hgg --config extensions.shelve= shelve
  shelved as Z
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hgg pull -u > /dev/null
  $ hgg --trace --config extensions.shelve= unshelve
  unshelving change 'Z'
  rebasing shelved changes
  $ hgg diff --stat
   test |  1 +
   1 files changed, 1 insertions(+), 0 deletions(-)


make the bookmark move by updating it on a, and then pulling with a local change
# add a commit to a
  $ cd ../a
  $ hgg up -C X |fgrep  "activating bookmark X"
  (activating bookmark X)
# go back to b, and check out X
  $ cd ../b
  $ hgg up -C X |fgrep  "activating bookmark X"
  (activating bookmark X)
# update and push from a
  $ make_changes ../a > /dev/null
  $ echo "more" >> test
  $ hgg pull -u 2>&1 | fgrep -v TESTTMP| fgrep -v "searching for changes" | fgrep -v adding
  pulling from $TESTTMP/a
  added 1 changesets with 0 changes to 0 files (+1 heads)
  updating bookmark X
  new changesets * (glob)
  updating to active bookmark X
  merging test
  warning: conflicts while merging test! (edit, then use 'hg resolve --mark')
  0 files updated, 0 files merged, 0 files removed, 1 files unresolved
  use 'hg resolve' to retry unresolved file merges
  $ hg update -C > /dev/null
  $ rm test.orig

make sure that commits aren't possible if working directory is not pointing to active bookmark
  $ assert_clean ../a
  $ assert_clean ../b
  $ hgg --cwd ../a id -i
  36a6e592ec06
  $ hgg --cwd ../a book | grep X
   \* X                         \d+:36a6e592ec06 (re)
  $ hgg --cwd ../b id -i
  36a6e592ec06
  $ hgg --cwd ../b book | grep X
   \* X                         \d+:36a6e592ec06 (re)
  $ make_changes ../a
  $ hgg --cwd ../a book | grep X
   \* X                         \d+:f73a71c992b8 (re)
  $ cd ../b
  $ hgg pull 2>&1 | grep updat
  updating bookmark X
  (run 'hg update' to get a working copy)
  $ hgg id -i # we're still on the old commit
  36a6e592ec06
  $ hgg book | grep X # while the bookmark moved
   \* X                         \d+:f73a71c992b8 (re)
  $ make_changes
  abort: Can't commit, working directory is not pointing to the active bookmark.
  Try: hg up X
  [255]
  $ hgg up X -t :local > /dev/null
  $ hgg id -i # the plus means pending changes
  f73a71c992b8+
  $ hgg book | grep X
   \* X                         \d+:f73a71c992b8 (re)
  $ hgg up -C > /dev/null # forget the changes
  $ hgg id -i
  f73a71c992b8
  $ assert_clean

