import fs from 'fs';
import path from 'path';

const ps1Path = './windows_desktop_deployment/setup_lexmind.ps1';
const outputDir = './extracted_sources';

if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
}

const content = fs.readFileSync(ps1Path, 'utf8');

// Find Write-Utf8File calls: Write-Utf8File "path" "base64"
const regex = /Write-Utf8File\s+"([^"]+)"\s+"([^"]+)"/g;
let match;
let count = 0;

while ((match = regex.exec(content)) !== null) {
    const filePath = match[1];
    const b64 = match[2];
    
    // Normalize path to something relative to /extracted_sources
    let cleanPath = filePath
        .replace('$workDir\\', '')
        .replace('$scriptsDir\\', 'scripts/')
        .replace('\\', '/');

    const targetPath = path.join(outputDir, cleanPath);
    const targetFolder = path.dirname(targetPath);
    if (!fs.existsSync(targetFolder)) {
        fs.mkdirSync(targetFolder, { recursive: true });
    }

    const decoded = Buffer.from(b64, 'base64');
    fs.writeFileSync(targetPath, decoded);
    console.log(`Extracted: ${cleanPath} to ${targetPath}`);
    count++;
}

console.log(`Successfully extracted ${count} assets.`);
