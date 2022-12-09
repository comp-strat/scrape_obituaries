# Command Line

We use the command line (bash) to work with git and run python scripts. 

If you use Mac or Linux operating system, then you can use the command line/terminal that comes with your operating system.

If you are a windows user, [install ubuntu](https://ubuntu.com/wsl) terminal environment on windows with WSL( Windows subsystem for Linux). Alternatively, you can also enable [Linux Bash Shell](https://www.howtogeek.com/249966/how-to-install-and-use-the-linux-bash-shell-on-windows-10/) on windows 10. 


# Python3

How to install Python3:
- [For Mac OS X](https://docs.python-guide.org/starting/install3/osx/)
- [For Windows](https://python-docs.readthedocs.io/en/latest/starting/install3/win.html)
- Alternatively, you can install Python3 by downloading the [Anaconda Distribution](https://www.anaconda.com/products/distribution). Anaconda can be used to install various Integrated Development Environments (IDE) such as [Jupyter notebook](https://www.geeksforgeeks.org/how-to-install-jupyter-notebook-in-windows/), Spyder etc. Jupyter notebook allows for interactive programming.


# GitHub

Github is a version control system which allows for collaboration. We have our [project's code respository ](https://github.com/comp-strat/obituaries)on github server. You need to have the appropriate permissions to access the code repository. 

Follow the [documentation](https://docs.github.com/en/get-started/onboarding/getting-started-with-your-github-account) to configure your github account. We will be using command line to interact with git.

In order to access the code respository, get your Github username added to the repository through admin. 

In order to further access the github repository through command line, you need to provide authentication through a personal access token. Therefore, [create a personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token).


# Virtual Machine

We use a virtual machine (VM) to run scripts that require high compute resources or long periods of time.

To access the VM:
- Get your Github username added to the VM by asking admin (Jaren)
- You need to [create and share a SSH key](https://docs.google.com/document/d/1fCG4At19jlcmPOgvQWkv-J-wJNNyqwXOVPN-9EAwzBk/edit#heading=h.ak0ehku9xpl5) in order to access the VM.
- Once your public SSH key is added to VM access protocol, you will be able to access the VM through the command line using an SSH client (uses your private key).


**Once you have set up your environments, follow the [SETUP.md](SETUP.md) to install packages.**