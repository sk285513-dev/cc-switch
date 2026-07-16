import fs from 'fs';
import path from 'path';

const ps1Path = './windows_desktop_deployment/setup_lexmind.ps1';
const inputDir = './extracted_sources';

if (!fs.existsSync(ps1Path)) {
    console.error(`Not found setup_lexmind.ps1 at ${ps1Path}`);
    process.exit(1);
}

let content = fs.readFileSync(ps1Path, 'utf8');

// We want to replace each Write-Utf8File "path" "base64" with local file content encoded into base64.
// To do this carefully, we can split or parse matches, but a precise regex replacement is very clean.
// Write-Utf8File\s+"([^"]+)"\s+"([^"]+)"
const regex = /Write-Utf8File\s+"([^"]+)"\s+"([^"]+)"/g;
let match;
let replacements = [];

while ((match = regex.exec(content)) !== null) {
    const fullMatch = match[0];
    const filePath = match[1];
    const oldB64 = match[2];
    
    let cleanPath = filePath
        .replace('$workDir\\', '')
        .replace('$scriptsDir\\', 'scripts/')
        .replace('\\', '/');

    const sourcePath = path.join(inputDir, cleanPath);
    if (fs.existsSync(sourcePath)) {
        const fileContent = fs.readFileSync(sourcePath);
        const newB64 = fileContent.toString('base64');
        replacements.push({
            fullMatch: fullMatch,
            filePath: filePath,
            newMatch: `Write-Utf8File "${filePath}" "${newB64}"`
        });
    } else {
        console.warn(`File not found: ${sourcePath}, leaving original base64 as-is.`);
    }
}

// Perform replacement
let updatedContent = content;
for (const r of replacements) {
    updatedContent = updatedContent.replace(r.fullMatch, r.newMatch);
}

fs.writeFileSync(ps1Path, updatedContent, 'utf8');
console.log(`Successfully packed ${replacements.length} assets from ${inputDir} back into ${ps1Path}`);
