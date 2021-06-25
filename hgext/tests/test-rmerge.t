init
  $ function init_repo() {
  > [ -e .hg ] && rm -r *.txt .hg
  > hg init
  > echo "[extensions]" >> .hg/hgrc
  > echo "rmerge=`dirname $TESTDIR`/rmerge.py" >> .hg/hgrc
  > hg book @
  > echo 'aaa' > a.txt; echo 'bbb' > b.txt; echo 'ccc' > c.txt; hg commit -Am'1' > /dev/null
  > }


rmerge
  $ init_repo
  $ hg book a
  $ echo AAA >> a.txt; hg commit -Am'a_1'
  $ hg co @
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (activating bookmark @)
  $ hg book b
  $ echo BBB >> b.txt; hg commit -Am'b_1'
  created new head
  $ hg rmerge a
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (activating bookmark a)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)
  bookmark b moved from * (glob)
  $ hg status
  M b.txt

rmerge-during-merge
  $ hg rmerge @
  abort: A merge is already in progress
  [255]

 rmerge-abort
  $ hg rmerge --abort
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (activating bookmark b)
  $ cat b.txt
  bbb
  BBB
  $ hg log -T '{rev} {desc}\n' -r '.%@'
  2 b_1
  $ hg rmerge --abort
  abort: There is no merge in progress
  [255]

rmerge-noop
  $ init_repo
  $ hg book a
  $ echo AAA >> a.txt; hg commit -Am'a_1'
  $ hg rmerge @
  no new changes in @

rmerge-ff
  $ init_repo
  $ hg book a --rev .
  $ echo AAA >> a.txt; hg commit -Am'_1'
  $ hg co a
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (activating bookmark a)
  $ hg rmerge @
  moving bookmark 'a' forward from * (glob)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (activating bookmark a)

