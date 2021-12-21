task_in_steps
=============

Many python-automation scripts can be seperated into steps. 
This library supports this seperation. You can define steps 
with classes. The steps are indepodent as they can implement 
`can_skip` which checks if the step can be skipped.

## Example

```python

class Config:

    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('--projectname', help='Name of the new project', required=True)
        self.parser.add_argument('--domain', help='Top-Level-Domain (without review.)', required=True)
        self.parser.add_argument('--template', help='A link to a GitHub-Repo, used as template', required=True)
        self.parser.add_argument('--username', help='LDAP Username', required=True)
        self.parser.add_argument('--password', help='LDAP Password (optional)', required=False)
        self.gerrit_port = 29418

    def load_args(self):
        args = self.parser.parse_args()
        self.project_name = args.projectname
        self.template_src = args.template
        self.gerrit_user = args.username
        self.password = args.password
        self.domain = args.domain
        self.gerrit_host = 'review.' + args.domain
        self.gerrit_url = f'http://{self.gerrit_host}'
        return self

if __name__ == "__main__":
    config = Config().load_args()

    run_steps(config, [
        CertificateOnThisMachine(),
        UploadSshKey(),
        ProjectFromTemplate(),
        CreateGerritProject(),
        ConfigureGerritGitHooks(),
        ConfigureGitPushToGerrit(),
        CreateJenkinsPipelines(),
        TriggerTemplateInit(),
        SendInitialCommit()
    ])

### The steps:

class CertificateOnThisMachine(Step):
    name = "SSH certificate on this machine"

    def __init__(self):
        home = os.path.expanduser('~')
        self.ssh_path = home + '/.ssh'

    def can_skip(self, config):
        return os.path.isfile(self.ssh_path + '/id_rsa.pub')

    def run(self, config):
        print('no ssh-certificate: generating one')
        os.system(f'ssh-keygen -t rsa -N '' -f {self.ssh_path}')
        return True


class UploadSshKey(Step):
    name = "Upload your SSH-Key"

    def can_skip(self, config):
        ssh_command = f'ssh -p {config.gerrit_port} {config.gerrit_user}@{config.gerrit_host} gerrit version'
        res = subprocess.run(ssh_command.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
        return res == 0

    def run(self, config):
        home = os.path.expanduser('~')
        ssh_path = home + '/.ssh'
        print()
        print('You did not upload your SSH-Key.')
        print()
        print(f'1. Go to: http://{config.gerrit_host}/settings/#SSHKeys')
        print( '2. Paste this in, click "Add Key" and run again:')
        with open(f'{ssh_path}/id_rsa.pub', 'r') as file:
            print(file.read())
        return False

class ProjectFromTemplate(Step):
    name = "Create project from template"

    def can_skip(self, config):
        return os.path.isdir(f'./{config.project_name}')

    def run(self, config):
        os.system(f'git clone {config.template_src} {config.project_name}')
        os.chdir(f'./{config.project_name}')
        os.system(f'rm .git -rf')
        os.system(f'git init')
        os.chdir('..')
        return True
    

class CreateGerritProject(Step):
    name = 'Create Gerrit project'

    def can_skip(self, config):
        command = f'ssh -p {config.gerrit_port} {config.gerrit_user}@{config.gerrit_host} gerrit ls-projects'
        existing_projects = subprocess.check_output(command, shell=True).decode().strip().split('\n')
        return config.project_name in existing_projects

    def run(self, config):
        os.chdir(f'./{config.project_name}')
        os.system(f'ssh -p {config.gerrit_port} {config.gerrit_user}@{config.gerrit_host} gerrit create-project {config.project_name}')
        os.chdir('..')
        return True


class ConfigureGerritGitHooks(Step):
    name = 'Installing Gerrit Git-Hooks'

    def can_skip(self, config):
        path = f'./{config.project_name}/.git/hooks/commit-msg'
        if not os.path.isfile(path):
            return False
        with open(path, 'r') as file:
            content = file.read()
            return 'Change-Id:' in content

    def run(self, config):
        os.chdir(f'./{config.project_name}')
        os.system(f'scp -p -P {config.gerrit_port} {config.gerrit_user}@{config.gerrit_host}:hooks/commit-msg ".git/hooks/"')
        os.chdir('..')
        return True
    

class ConfigureGitPushToGerrit(Step):
    name = 'Configure "git push" to Gerrit'

    def can_skip(self, config):
        path = f'./{config.project_name}/.git/config'
        if not os.path.isfile(path):
            return False
        with open(path, 'r') as file:
            content = file.read()
            return 'push = refs/heads/master:refs/for/master' in content
    
    def run(self, config):
        path = f'./{config.project_name}/.git/config'
        git_config = f'''
[core]
        repositoryformatversion = 0
        filemode = true
        bare = false
        logallrefupdates = true
[remote "origin"]
        url = ssh://{config.gerrit_user}@{config.gerrit_host}:{config.gerrit_port}/{config.project_name}
        fetch = +refs/heads/master:refs/remotes/origin/master
        push = refs/heads/master:refs/for/master
[branch "master"]
        remote = origin
        merge = refs/heads/master
'''
        with open(path, 'w') as f:
            f.write(git_config)
        return True

class CreateJenkinsPipelines(Step):
    name = 'Creating Jenkins-Pipelines'

    def can_skip(self, config):
        job1 = config.project_name + '-code'
        job2 = config.project_name + '-deploy'

        server = self._get_server(config)
        jobs = [job['name'] for job in server.get_all_jobs()]
        
        return job1 in jobs and job2 in jobs


    def run(self, config):
        self._create_pipeline(config.project_name, 'code', config)
        self._create_pipeline(config.project_name, 'deploy', config)
        return True

    def _get_server(self, config):
        if hasattr(self, 'server'):
            return self.server

        url = f'http://ci.{config.domain}'

        password = config.password
        if not password:
            print(f'Enter credentials for "{url}"')
            print(f'User: {config.gerrit_user}')
            password = getpass()

        self.server = Jenkins(
            url, 
            username=config.gerrit_user, 
            password=password)
        
        return self.server


    def _create_pipeline(self, project_name, pipeline_type, config):
        content = pkg_resources.resource_string('generate_gerrit_jenkins_project', f'jobs/{pipeline_type}.config.xml').decode()
        content = content.replace('helloworld', project_name)

        try:
            self._get_server(config).create_job(project_name + '-' + pipeline_type, content)
        except JenkinsException as e:
            print(e)
            raise

class TriggerTemplateInit(Step):
    name = 'Trigger Template Init'

    def can_skip(self, config):
        return not os.path.isfile(f'./{config.project_name}/init_template.py')

    def run(self, config):
        stdout, stderr, has_error = exec(f'python3 init_template.py', cwd=f'./{config.project_name}')
        if not has_error:
            exec(f'rm init_template.py', cwd=f'./{config.project_name}')
        return not has_error

class SendInitialCommit(Step):
    name = 'Send initial commit to gerrit'

    def can_skip(self, config):
        stdout, stderr, has_error = exec('git log', cwd=f'./{config.project_name}')
        return not has_error # git log returns error if there are not commits. Skip=True if no error returned
    
    def run(self, config):
        stdout, stderr, has_error1 = exec('git add .', cwd=f'./{config.project_name}')
        print(stdout, stderr)
        stdout, stderr, has_error2 = exec('git commit -aminit', cwd=f'./{config.project_name}')
        print(stdout, stderr)
        stdout, stderr, has_error3 = exec('git push origin master', cwd=f'./{config.project_name}')
        print(stdout, stderr)
        return True

```