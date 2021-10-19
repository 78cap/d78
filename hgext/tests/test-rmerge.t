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
  bookmark a will be merged to @ when work is finished.
  run hg rmerge periodically to get the latest from there.
  $ echo AAA >> a.txt; hg commit -Am'a_1'
  bookmark a is now 0 revisions behind, and 1 ahead of @
  $ hg co @
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (activating bookmark @)
  $ hg book b
  bookmark b will be merged to @ when work is finished.
  run hg rmerge periodically to get the latest from there.
  $ echo BBB >> b.txt; hg commit -Am'b_1'
  created new head
  bookmark b is now 0 revisions behind, and 1 ahead of @
  $ hg merge a
  abort: Merging b and a is discouraged, add --anyrev if you really have to
  [255]
  $ hg rmerge a
  2 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (activating bookmark a)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)
  bookmark b moved from * (glob)
  (note that yours/theirs and local/server is reversed during merge conflict resolution, yours=a, theirs=b)
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
  bookmark a will be merged to @ when work is finished.
  run hg rmerge periodically to get the latest from there.
  $ echo AAA >> a.txt; hg commit -Am'a_1'
  bookmark a is now 0 revisions behind, and 1 ahead of @
  $ hg rmerge @
  no new changes in @

rmerge-ff
  $ init_repo
  $ hg book a --rev .
  $ echo AAA >> a.txt; hg commit -Am'_1'
  bookmark @ is now 0 revisions behind, and 0 ahead of @
  $ hg co a
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (activating bookmark a)
  $ hg rmerge @
  moving bookmark 'a' forward from * (glob)
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (activating bookmark a)

