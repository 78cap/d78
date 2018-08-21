"""implements bookmark-based branching

 - Disables creation of new branches (config: enable_branches=False).
 - Requires an active bookmark on commit (config: require_bookmark=True).
 - Doesn't move the active bookmark on update, only on commit.
 - Requires '--rev' for moving an existing bookmark.
 - Protects special bookmarks (config: protect=@).

 flow related commands

    :hg book MARK: create a new bookmark
    :hg book MARK -r REV: move bookmark to revision (fast-forward)
    :hg up|co MARK: switch to bookmark
    :hg push -B .: push active bookmark
"""
from mercurial.i18n import _
from mercurial import (
    bookmarks,
    error,
    registrar,
    commands,
    extensions
)

MY_NAME = __name__[len('hgext_'):] if __name__.startswith('hgext_') else __name__

configtable = {}
configitem = registrar.configitem(configtable)

configitem(MY_NAME, 'protect', ['@'])
configitem(MY_NAME, 'require_bookmark', True)
configitem(MY_NAME, 'enable_branches', False)

cmdtable = {}
command = registrar.command(cmdtable)


def commit_hook(ui, repo, **kwargs):
    active = repo._bookmarks.active
    if active:
        if active in ui.configlist(MY_NAME, 'protect'):
            raise error.Abort(_('Can\'t commit, bookmark {} is protected').format(active))
        if not cwd_at_bookmark(repo, active):
            raise error.Abort(_('Can\'t commit, working directory out of sync with active bookmark.\nRun: hg up {}').format(active))
    elif ui.configbool(MY_NAME, 'require_bookmark', True):
        raise error.Abort(_('Can\'t commit without an active bookmark'))
    return 0


def bookmarks_update(orig, repo, parents, node):
    if len(parents) == 2:
        return orig(repo, parents, node)
    else:
        return False


def bookmarks_addbookmarks(orig, repo, tr, names, rev=None, force=False, inactive=False):
    if not rev:
        marks = repo._bookmarks
        for name in names:
            if name in marks:
                raise error.Abort("Bookmark {} already exists, to move use the --rev option".format(name))
    return orig(repo, tr, names, rev, force, inactive)


def commands_commit(orig, ui, repo, *args, **opts):
    commit_hook(ui, repo)
    return orig(ui, repo, *args, **opts)


def commands_pull(orig, ui, repo, *args, **opts):
    rc = orig(ui, repo, *args, **opts)
    active = repo._bookmarks.active
    if active and not cwd_at_bookmark(repo, active):
        ui.warn("Working directory out of sync with active bookmark.\nRun: hg up {}\n".format(active))
    return rc


def cwd_at_bookmark(repo, mark):
    mark_id = repo._bookmarks[mark]
    cur_id = repo.lookup('.')
    return cur_id == mark_id


def commands_branch(orig, ui, repo, label=None, **opts):
    if label and not opts.get('clean') and not opts.get('rev'):
        raise error.Abort("Branching should be done using bookmarks:\nhg bookmark " + label)
    return orig(ui, repo, label, **opts)


def reposetup(ui, repo):
    extensions.wrapfunction(bookmarks, 'update', bookmarks_update)
    extensions.wrapfunction(bookmarks, 'addbookmarks', bookmarks_addbookmarks)
    # commit hook conflicts with shelving
    # ui.setconfig('hooks', 'pretxncommit.' + MY_NAME, commit_hook, source=MY_NAME)


def uisetup(ui):
    extensions.wrapcommand(commands.table, 'commit', commands_commit)
    extensions.wrapcommand(commands.table, 'pull', commands_pull)
    if not ui.configbool(MY_NAME, 'enable_branches'):
        extensions.wrapcommand(commands.table, 'branch', commands_branch)
