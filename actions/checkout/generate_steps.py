import subprocess
import os


def main():
    def get_arg(name, default: str = main):
        evar = os.getenv('A_' + name, default)
        if evar == main:
            raise ValueError(f'Missing environment variable {name}')
        return evar
    a_repository = get_arg('REPOSITORY')
    a_gitdir = get_arg('GITDIR')
    a_output = get_arg('OUTPUT')
    a_repo_secrets_pattern = get_arg('SECRETS_NAME_PATTERN', '{name}')
    a_repo_secrets = get_arg('SECRETS', '')
    a_fetch_depth = get_arg('FETCH_DEPTH')
    a_refs = get_arg('REFS')

    repo_secrets_dict = None
    no_pattern = False

    def get_repo_secret(rr_name):
        rr_secret_name = rr_name if no_pattern else a_repo_secrets_pattern.replace('{name}', rr_name.replace("-", "_")).upper()
        if repo_secrets_dict:
            r_secret = repo_secrets_dict.get(rr_secret_name)
            if not r_secret:
                raise ValueError(f'Secret {rr_secret_name} for repo {rr_name} not found')
            return ('token' if r_secret.startswith('github_pat_') else 'ssh-key'), r_secret
        else:
            return 'ssh-key', '${{ secrets.' + rr_secret_name + ' }}'

    if a_repo_secrets:
        if a_repo_secrets.startswith('{'):
            import json
            repo_secrets_dict = json.loads(a_repo_secrets)
        else:
            no_pattern = True
            repo_secrets_dict = dict()
            last_var = None
            for line in a_repo_secrets.splitlines():
                line = line.strip()
                if line.startswith('#'):
                    continue
                if ':' in line:
                    last_var, value = line.split(':', maxsplit=1)
                    last_var = last_var.strip()
                    repo_secrets_dict[last_var] = value.strip()
                elif last_var:
                    repo_secrets_dict[last_var] += f'\n{line}'

    repo_org = os.path.dirname(a_repository)
    repo_name = os.path.basename(a_repository)
    this_repo_checkout_props = dict()
    checkouts = {repo_name: this_repo_checkout_props}
    corepos_file = os.path.join(a_gitdir, '.corepos')
    if os.path.exists(corepos_file):
        with open(corepos_file, 'r') as f:
            corepos_lines = f.readlines()
        names = []
        for i in range(len(corepos_lines)):
            line = corepos_lines[i].strip()
            if line.startswith('[repo ') and line.endswith(']'):
                line = line[1:-1].replace("'", "").replace('"', '')
                r_name = line.split(' ')[-1]
                names.append(r_name)
                corepos_lines[i] = f'[corepo_{r_name}]\n'
        #
        import configparser
        cp = configparser.ConfigParser()
        cp.read_file(corepos_lines, corepos_file)

        if names:
            this_repo_path = cp.get('repo', 'path', fallback=repo_name).replace('{name}', repo_name)
            this_repo_checkout_props['path'] = this_repo_path

            for r_name in names:
                secret_key, secret_val = get_repo_secret(r_name)
                repo_props = {
                    'repository': f'{repo_org}/{r_name}',
                    secret_key: secret_val
                }
                section_name = f'corepo_{r_name}'
                r_path = cp.get(section_name, 'path', fallback=None)
                if r_path != '{root}':
                    if not r_path:
                        r_path = r_name if '/' not in this_repo_path else os.path.join(os.path.dirname(this_repo_path), r_name)
                    repo_props['path'] = r_path.replace('{name}', r_name).replace('{root}/', '')
                checkouts[r_name] = repo_props

            if a_refs == 'by-commit':
                rc = subprocess.run(['git', '-C', a_gitdir, 'log', '--format=%(trailers:key=Co-repos,valueonly)', '-1'], capture_output=True)
                trailer = rc.stdout.decode('utf-8').strip()
                if trailer:
                    for t_corepo in trailer.split(','):
                        if '@' in t_corepo:
                            t_corepo = t_corepo.strip()
                            t_name, t_hash = t_corepo.split('@', maxsplit=1)
                            if t_name in checkouts:
                                checkouts[t_name]['ref'] = t_hash
                else:
                    raise ValueError(f'No Co-repos trailer in {os.getenv("GITHUB_REPOSITORY", "GITHUB_REPOSITORY")}@{os.getenv("GITHUB_SHA", "GITHUB_SHA")[0:12]}')
            elif a_refs == 'by-ref':
                main_ref = os.getenv('GITHUB_REF_NAME')
                if not main_ref:
                    raise ValueError('GITHUB_REF_NAME is not set')
                for checkout in checkouts.values():
                    checkout['ref'] = main_ref
            elif a_refs != 'main' and a_refs != '':
                for checkout in checkouts.values():
                    checkout['ref'] = a_refs

    txt = f'''\
name: 'checkout others'
description: 'Checks out sources for repo and its corepos'
runs:
  using: "composite"
  steps:
    - id: rm_generated
      run: rm {a_output}
      shell: bash
'''
    # top level dirs get checked out before lower level
    for r_name, checkout in sorted(checkouts.items(), key=lambda item: item[1].get('path', '')):
        txt += f'''\
    - id: checkout_{r_name}
      uses: actions/checkout@v4
'''
        if a_fetch_depth != '1':
            checkout['fetch-depth'] = a_fetch_depth
        if checkout:
            txt += '      with:\n'
        for n, v in checkout.items():
            if '\n' not in v:
                txt += f'        {n}: \'{v}\'\n'
            else:
                new_line = '\n          '
                txt += f'        {n}: |{new_line}' + v.strip().replace('\n', new_line) + '\n'
    os.makedirs(os.path.dirname(a_output), exist_ok=True)
    with open(a_output, 'w') as f:
        f.write(txt)


if __name__ == '__main__':
    main()
