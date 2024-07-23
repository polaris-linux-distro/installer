import subprocess

def get_gpu_vendor():
    try:
        # Execute the lshw command to get hardware details
        output = subprocess.check_output(['lshw', '-C', 'display'], universal_newlines=True)
        
        # Check for different GPU vendors
        if 'Intel' in output:
            return 'intel'
        elif 'VMware' in output:
            return 'vmware'
        elif 'Advanced Micro Devices' in output or 'AMD' in output:
            return 'amd'
        elif 'NVIDIA' in output:
            # Determine the NVIDIA architecture (simplified example)
            if 'TU1' in output or 'Turing' in output:
                return 'nvidia_turingplus'
            else:
                return 'nvidia_beforeturing'
        else:
            return 'unknown'
    except Exception as e:
        return str(e)