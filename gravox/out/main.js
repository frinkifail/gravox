"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.deactivate = exports.activate = void 0;
const vscode = require("vscode");
const node_1 = require("vscode-languageclient/node");
let client;
function activate(context) {
    // Server options - how to start your LSP server
    const serverOptions = {
        command: '.venv/bin/python',
        args: ['-m', 'lsp.newlsp.lsp'],
        transport: node_1.TransportKind.stdio
    };
    // Client options - which files to send to the server
    const clientOptions = {
        documentSelector: [{ scheme: 'file', language: 'gravox' }],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/.grv')
        }
    };
    // Create and start the language client
    client = new node_1.LanguageClient('gravoxLanguageServer', 'Gravox LSP', serverOptions, clientOptions);
    // Start the client (and server)
    client.start();
}
exports.activate = activate;
// function getServerPath(): string {
//     const config = vscode.workspace.getConfiguration('mylanguage');
//     const serverPath = config.get<string>('server.path');
//     if (serverPath) {
//         return serverPath;
//     }
//     // Try to find it in common locations
//     const possiblePaths = [
//         'gravox-lsp',
//         'python -m lsp.lsp',
//         // add more possibilities
//     ];
//     // Return first available or default
//     return possiblePaths[0];
// }
function deactivate() {
    if (!client) {
        return undefined;
    }
    return client.stop();
}
exports.deactivate = deactivate;
//# sourceMappingURL=main.js.map