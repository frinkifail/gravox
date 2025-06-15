import * as vscode from 'vscode';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    TransportKind
} from 'vscode-languageclient/node';

let client: LanguageClient;

export function activate(context: vscode.ExtensionContext) {
    // Server options - how to start your LSP server
    const serverOptions: ServerOptions = {
        command: '.venv/bin/python',  // or path to your executable
        args: ['-m', 'lsp.newlsp.lsp'],
        transport: TransportKind.stdio
    };

    // Client options - which files to send to the server
    const clientOptions: LanguageClientOptions = {
        documentSelector: [{ scheme: 'file', language: 'gravox' }],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/.grv')
        }
    };

    // Create and start the language client
    client = new LanguageClient(
        'gravoxLanguageServer',
        'Gravox LSP',
        serverOptions,
        clientOptions
    );

    // Start the client (and server)
    client.start();
}

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

export function deactivate(): Thenable<void> | undefined {
    if (!client) {
        return undefined;
    }
    return client.stop();
}