const axios = require('axios');
const fs = require('fs-extra');
const tmp = require('tmp');
const { execSync } = require('child_process');

const SCHEMA_URL = 'http://localhost:5000/apispec_1.json';  
const LOCAL_SCHEMA_PATH = 'src/api/apispec_1.json';
const SOURCE_PATH = 'src/client';

async function downloadSchema() {
    try {
        const response = await axios.get(SCHEMA_URL, { responseType: 'stream' });
        const writer = fs.createWriteStream(LOCAL_SCHEMA_PATH);
        response.data.pipe(writer);
        return new Promise((resolve, reject) => {
            writer.on('finish', resolve);
            writer.on('error', reject);
        });
    } catch (error) {
        console.log(error.code);
        console.warn("Couldn't download schema, using the existing one.");
    }
}

function generateClient() {
    const tempDir = tmp.dirSync({ prefix: 'openapi-client-gen-', unsafeCleanup: true });
    try {
        execSync(`openapi-generator-cli generate -i ${LOCAL_SCHEMA_PATH} -g javascript -o ${tempDir.name}`);
        return tempDir.name;
    } catch (error) {
        console.error('Error generating client:', error);
        tempDir.removeCallback(); // Cleanup
        process.exit(1);
    }
}

function copySourceToDestination(tmpDir) {
    const sourceDir = `${tmpDir}/src`; // Adjust based on the actual structure if needed
    fs.copySync(sourceDir, SOURCE_PATH);
}

(async function main() {
    await downloadSchema();
    const tempDir = generateClient();
    copySourceToDestination(tempDir);
})();
