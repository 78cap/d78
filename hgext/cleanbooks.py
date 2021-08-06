"""provides utilities for bookmarks cleanup
"""
from mercurial.i18n import _
from mercurial import (
    registrar,
    cmdutil,
    bookmarks,
    hg,
    encoding,
    phases,
)
from mercurial.utils import stringutil
import binascii

cmdtable = {}
command = registrar.command(cmdtable)

def get_remote_names(ui, source, namespace=b'bookmarks'):
    remotepath = ui.expandpath(source)
    remoterepo = hg._peerlookup(remotepath).instance(ui, remotepath, create=False)
    with remoterepo.commandexecutor() as e:
        rnames = e.callcommand(
            b'listkeys',
            {
                b'namespace': namespace,
            },
        ).result()
    return rnames

@command(b'remotebookmarks',
    cmdutil.formatteropts + cmdutil.remoteopts,
    helpcategory=command.CATEGORY_MISC,
)
def cmd_rbookmarks(ui, repo, source=b"default", **opts):
    """list remote bookmarks"""
    bmarks = get_remote_names(ui, source)
    _print_bookmarks(ui, repo, bmarks, opts, print_bookmarks_msg=True)

@command(b'cleanbookmarks', [
             (b'a', b'all', False, _(b'include un-pushed or user bookmarks')),
         ] + cmdutil.logopts + cmdutil.remoteopts + cmdutil.dryrunopts,
         helpcategory=command.CATEGORY_MISC,
         )
def cmd_cleanbookmarks(ui, repo, source=b"default", **opts):
    """delete bookmarks that only exist locally, likely removed remotely.

    By default exclude drafts and commits authored by current user"""
    remotemarks = get_remote_names(ui, source)
    n_bookmarks, divergent = _normalize_bookmarks(repo, source)
    r = bookmarks.comparebookmarks(repo, remotemarks, n_bookmarks)
    addsrc, adddst, advsrc, advdst, diverge, differ, invalid, same = r
    cur_user = stringutil.shortuser(ui.username())
    result = dict()
    include_all = opts.get(b'all')
    for bname, rhash, lhash in adddst:
        if bname in divergent:
            bname_l, h_s = divergent[bname]
            if h_s and (include_all or not _is_unpushed(repo, h_s, cur_user)):
                result[bname] = binascii.hexlify(h_s)
            bname = bname_l
        if include_all or not _is_unpushed(repo, lhash, cur_user):
            result[bname] = binascii.hexlify(lhash)

    if result:
        _print_bookmarks(ui, repo, result, opts)
        if not opts.get(b'dry_run'):
            r = ui.prompt(_(b'delete? (y/n): '), default=b'n') if ui.interactive() else b'y'
            if r in b'yY':
                with repo.wlock(), repo.lock(), repo.transaction(b'bookmark') as tr:
                    bookmarks.delete(repo, tr, result.keys())
                ui.status(_(b"deleted %d bookmark(s)\n" % len(result)))
            else:
                ui.status(_(b"canceled removal of %d bookmark(s)\n" % len(result)))
        else:
            ui.status(_(b"dry-run: not deleting %d bookmark(s)\n" % len(result)))
    else:
        ui.status(_(b"no local only bookmarks\n"))


@command(b'diffbookmarks', cmdutil.logopts + cmdutil.remoteopts,
         helpcategory=command.CATEGORY_MISC,
         )
def cmd_diffbookmarks(ui, repo, source=b"default", **opts):
    """compare local and remote bookmarks

    The codes are::

      A = added remotely
      M = modified remotely
      R = removed remotely
      C = diverged
      ? = not known remotely

    By default exclude drafts and commits authored by current user"""
    remotemarks = get_remote_names(ui, source)
    n_bookmarks, divergent = _normalize_bookmarks(repo, source)
    r = bookmarks.comparebookmarks(repo, remotemarks, n_bookmarks)
    for rlist in r:
        for i in range(len(rlist)):
            name, rhash, lhash = rlist[i]
            d = divergent.get(name)
            if d:
                bname_l, h_s = d
                rlist[i] = (bname_l, rhash, lhash)
    addsrc, adddst, advsrc, advdst, diverge, differ, invalid, same = r
    cur_user = stringutil.shortuser(ui.username())
    empty_hash = b'0'*40
    def fmt_hashes(lhash, rhash):
        if lhash:
            lhash = binascii.hexlify(lhash)
        return (lhash or empty_hash) + b'   ' + (rhash or empty_hash)

    adddst_u = {name: fmt_hashes(lhash, rhash) for name, rhash, lhash in adddst if _is_unpushed(repo, lhash, cur_user)}
    adddst_r = {name: fmt_hashes(lhash, rhash) for name, rhash, lhash in adddst if name not in adddst_u}
    results = [
        ({name: fmt_hashes(lhash, rhash) for name, rhash, lhash in addsrc}, 'A'),
        ({name: fmt_hashes(lhash, rhash) for name, rhash, lhash in differ}, 'M'),
        ({name: fmt_hashes(lhash, rhash) for name, rhash, lhash in advsrc}, 'M'),
        ({name: fmt_hashes(lhash, rhash) for name, rhash, lhash in advdst}, 'M'),
        ({name: fmt_hashes(lhash, rhash) for name, rhash, lhash in diverge if binascii.hexlify(lhash) != rhash}, 'C'),
        (adddst_r, 'R'),
        (adddst_u, '?'),
    ]
    pad_length = 0
    for bmarks, state in results:
        for n in bmarks.keys(): pad_length = max(pad_length, len(n))
    for bmarks, state in results:
        _print_bookmarks(ui, repo, bmarks, opts, prefix=state, pad_length=pad_length)

def _is_unpushed(repo, lhash, cur_user=None):
    ctx = repo[lhash]
    if not cur_user:
        return ctx.phase() > phases.public
    c_user = stringutil.shortuser(ctx.user())
    return c_user == cur_user or ctx.phase() > phases.public

def _print_bookmarks(ui, repo, bmarks, opts, prefix='', print_bookmarks_msg=False, pad_length=0):
    pad_length = pad_length or (max(len(name) for name in bmarks.keys()) if bmarks else 25)
    with ui.formatter(b'bookmarks', opts) as fm:
        if len(bmarks) == 0 and fm.isplain() and print_bookmarks_msg:
            ui.status(_(b"no bookmarks set\n"))
        label = ''
        for bmark in sorted(bmarks.keys()):
            h = bmarks[bmark]
            fm.startitem()
            fm.context(repo=repo)
            if not ui.quiet:
                fm.plain(b' %s ' % prefix, label=label)
            fm.write(b'bookmark', b'%s', bmark, label=label)
            pad = b" " * (pad_length - encoding.colwidth(bmark))
            fm.condwrite(
                not ui.quiet,
                b'node',
                pad + b' %s',
                h,
                label=label,
            )
            fm.data(active=False)
            fm.plain(b'\n')

def _normalize_bookmarks(repo, source):
    """removes @default suffixes from bookmarks, returns new dict, and another dict shortname: long_name, long_hash, short_hash, is_unpushed"""
    suffix = b'@' + source
    bookmarks = repo._bookmarks
    n_bookmarks = dict()
    divergent = dict()
    for bm, h in bookmarks.items():
        n_bookmarks[bm] = h
    for bm, h in bookmarks.items():
        if bm.endswith(suffix):
            bm_shortname = bm[0:-len(suffix)]
            n_bookmarks[bm_shortname] = h
            del n_bookmarks[bm]
            divergent[bm_shortname] = (bm, bookmarks.get(bm_shortname))
    return n_bookmarks, divergent
