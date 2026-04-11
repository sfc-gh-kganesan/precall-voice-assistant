import Docker from 'dockerode';

const docker = new Docker({ socketPath: '/var/run/docker.sock' });

async function checkGvisorAvailability() {
  console.log('╔════════════════════════════════════════════════╗');
  console.log('║   P67 gVisor Availability Check                ║');
  console.log('╚════════════════════════════════════════════════╝\n');

  const info = await docker.info();
  
  console.log('System Info:');
  console.log(`  OS: ${info.OperatingSystem}`);
  console.log(`  Kernel: ${info.KernelVersion}`);
  console.log(`  Architecture: ${info.Architecture}`);
  console.log(`  Docker Runtime: ${info.DefaultRuntime}`);
  console.log('');

  const runtimes = info.Runtimes || {};
  console.log('Available Runtimes:');
  
  for (const [name, config] of Object.entries(runtimes)) {
    console.log(`  - ${name}: ${config.path || 'default'}`);
  }
  
  const hasGvisor = 'runsc' in runtimes || 'gvisor' in runtimes;
  
  console.log('');
  if (hasGvisor) {
    console.log('✓ gVisor (runsc) is available!');
    console.log('  Run: npm run benchmark');
    
    console.log('\nTesting gVisor...');
    try {
      const container = await docker.createContainer({
        Image: 'alpine:latest',
        Cmd: ['echo', 'gVisor works!'],
        HostConfig: {
          Runtime: 'runsc',
        },
      });
      
      await container.start();
      const result = await container.wait();
      const logs = await container.logs({ stdout: true, stderr: true });
      await container.remove();
      
      console.log(`  Output: ${logs.toString().trim()}`);
      console.log('  ✓ gVisor container ran successfully');
    } catch (err) {
      console.log(`  ✗ gVisor test failed: ${err.message}`);
    }
  } else {
    console.log('✗ gVisor (runsc) is NOT available');
    console.log('');
    console.log('To install gVisor on Linux:');
    console.log('  curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg');
    console.log('  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | sudo tee /etc/apt/sources.list.d/gvisor.list');
    console.log('  sudo apt-get update && sudo apt-get install -y runsc');
    console.log('');
    console.log('Note: gVisor is not supported on macOS (Docker Desktop).');
    console.log('Run this benchmark on a Linux machine or SPCS.');
  }
  
  return hasGvisor;
}

checkGvisorAvailability().catch(console.error);
