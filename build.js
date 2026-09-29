// Simple build script - copy files to dist/
const fs = require('fs');
const path = require('path');

const distDir = 'dist';

// Create dist directory
if (!fs.existsSync(distDir)) {
  fs.mkdirSync(distDir, { recursive: true });
}

// Copy index.html
fs.copyFileSync('index.html', path.join(distDir, 'index.html'));
console.log('✓ Copied index.html');

// Copy public/ files
const publicDir = 'public';
if (fs.existsSync(publicDir)) {
  const files = fs.readdirSync(publicDir);
  files.forEach(file => {
    const src = path.join(publicDir, file);
    const dest = path.join(distDir, file);
    fs.copyFileSync(src, dest);
    console.log(`✓ Copied ${file}`);
  });
}

console.log('\n✅ Build complete!');
