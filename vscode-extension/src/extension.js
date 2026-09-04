const vscode = require("vscode");

const KEYWORDS = ["class", "var", "list", "if", "elseif", "else", "while", "for", "try", "catch", "throw", "goto", "ment", "mentions"];
const TYPES = ["int", "str", "float", "bool", "ptr"];
const BUILTINS = ["print", "input", "ascii", "video"];
const BOOLEAN_LITERALS = ["true", "false"];

function keywordCompletions() {
  return KEYWORDS.map((word) => {
    const item = new vscode.CompletionItem(word, vscode.CompletionItemKind.Keyword);
    return item;
  });
}

function typeCompletions() {
  return TYPES.map((word) => {
    const item = new vscode.CompletionItem(word, vscode.CompletionItemKind.TypeParameter);
    return item;
  });
}

function builtinCompletions() {
  const items = [];

  const print = new vscode.CompletionItem("print", vscode.CompletionItemKind.Function);
  print.detail = "print(<expression>);";
  print.insertText = new vscode.SnippetString('print(${1:value});');
  items.push(print);

  const input = new vscode.CompletionItem("input", vscode.CompletionItemKind.Function);
  input.detail = 'input("<prompt>")';
  input.insertText = new vscode.SnippetString('input("${1:prompt}")');
  items.push(input);

  const asciiStmt = new vscode.CompletionItem("ascii", vscode.CompletionItemKind.Function);
  asciiStmt.detail = "ascii <expression>; - prints an image as ASCII art";
  asciiStmt.insertText = new vscode.SnippetString('ascii "${1:image.png}";');
  items.push(asciiStmt);

  const videoStmt = new vscode.CompletionItem("video", vscode.CompletionItemKind.Function);
  videoStmt.detail = "video <expression>; - plays a video as ASCII art";
  videoStmt.insertText = new vscode.SnippetString('video "${1:clip.mp4}";');
  items.push(videoStmt);

  const parseCall = new vscode.CompletionItem("parse", vscode.CompletionItemKind.Method);
  parseCall.detail = "<str variable>.parse(<type>)";
  parseCall.insertText = new vscode.SnippetString("parse(${1|int,float,bool,str|})");
  items.push(parseCall);

  const appendCall = new vscode.CompletionItem("append", vscode.CompletionItemKind.Method);
  appendCall.detail = "<list>.append(<expression>)";
  appendCall.insertText = new vscode.SnippetString("append(${1:value})");
  items.push(appendCall);

  const lengthCall = new vscode.CompletionItem("length", vscode.CompletionItemKind.Method);
  lengthCall.detail = "<list>.length()";
  lengthCall.insertText = new vscode.SnippetString("length()");
  items.push(lengthCall);

  return items;
}

function booleanCompletions() {
  return BOOLEAN_LITERALS.map((word) => {
    return new vscode.CompletionItem(word, vscode.CompletionItemKind.Value);
  });
}

function snippetCompletions() {
  const items = [];

  const mainClass = new vscode.CompletionItem("class main", vscode.CompletionItemKind.Snippet);
  mainClass.insertText = new vscode.SnippetString(
    "class main() {\n\t$0\n}"
  );
  mainClass.detail = "Program entry point";
  items.push(mainClass);

  const initClass = new vscode.CompletionItem("class init", vscode.CompletionItemKind.Snippet);
  initClass.insertText = new vscode.SnippetString(
    "class init() {\n\t$0\n}"
  );
  initClass.detail = "Runs once, before main";
  items.push(initClass);

  const mentClass = new vscode.CompletionItem("class (ment)", vscode.CompletionItemKind.Snippet);
  mentClass.insertText = new vscode.SnippetString(
    "class ${1:Name}(ment) {\n\t$0\n}"
  );
  mentClass.detail = "Class callable from other files via @mentions";
  items.push(mentClass);

  const varDecl = new vscode.CompletionItem("var", vscode.CompletionItemKind.Snippet);
  varDecl.insertText = new vscode.SnippetString(
    "var ${1:name}: ${2|int,str,float,bool|} = ${3:value};"
  );
  varDecl.detail = "Variable declaration";
  items.push(varDecl);

  const ifStmt = new vscode.CompletionItem("if", vscode.CompletionItemKind.Snippet);
  ifStmt.insertText = new vscode.SnippetString("if (${1:condition}) {\n\t$0\n}");
  items.push(ifStmt);

  const whileStmt = new vscode.CompletionItem("while", vscode.CompletionItemKind.Snippet);
  whileStmt.insertText = new vscode.SnippetString("while (${1:condition}) {\n\t$0\n}");
  items.push(whileStmt);

  const forStmt = new vscode.CompletionItem("for", vscode.CompletionItemKind.Snippet);
  forStmt.insertText = new vscode.SnippetString(
    "for (var ${1:i}: int = 0; ${1:i} < ${2:10}; ${1:i} += 1) {\n\t$0\n}"
  );
  items.push(forStmt);

  const mentionStmt = new vscode.CompletionItem("@mentions", vscode.CompletionItemKind.Snippet);
  mentionStmt.insertText = new vscode.SnippetString(
    "@mentions ${1:file}.el -> ${2:alias};"
  );
  items.push(mentionStmt);

  const tryStmt = new vscode.CompletionItem("try", vscode.CompletionItemKind.Snippet);
  tryStmt.insertText = new vscode.SnippetString(
    "try {\n\t$1\n}\ncatch (${2:e}: str) {\n\t$0\n}"
  );
  tryStmt.detail = "try { ... } catch (e: str) { ... }";
  items.push(tryStmt);

  const throwStmt = new vscode.CompletionItem("throw", vscode.CompletionItemKind.Snippet);
  throwStmt.insertText = new vscode.SnippetString('throw "${1:message}";');
  items.push(throwStmt);

  const gotoStmt = new vscode.CompletionItem("goto", vscode.CompletionItemKind.Snippet);
  gotoStmt.insertText = new vscode.SnippetString("goto ln: ${1:1};");
  gotoStmt.detail = "goto ln: <line number>; - jump to a top-level statement in this class";
  items.push(gotoStmt);

  const ptrDecl = new vscode.CompletionItem("ptr", vscode.CompletionItemKind.Snippet);
  ptrDecl.insertText = new vscode.SnippetString(
    "var ${1:p}: ptr<${2|int,str,float,bool|}> = &${3:variable};"
  );
  ptrDecl.detail = "Pointer variable declaration";
  items.push(ptrDecl);

  const listDecl = new vscode.CompletionItem("list", vscode.CompletionItemKind.Snippet);
  listDecl.insertText = new vscode.SnippetString(
    "list ${1:name}: [${2:item1}, ${3:item2}];"
  );
  listDecl.detail = "List declaration";
  items.push(listDecl);

  const typedListDecl = new vscode.CompletionItem("list<type>", vscode.CompletionItemKind.Snippet);
  typedListDecl.insertText = new vscode.SnippetString(
    "list<${1|int,str,float,bool|}> ${2:name}: [${3:item1}, ${4:item2}];"
  );
  typedListDecl.detail = "Typed list declaration";
  items.push(typedListDecl);

  return items;
}

function activate(context) {
  const provider = vscode.languages.registerCompletionItemProvider(
    "evanslang",
    {
      provideCompletionItems() {
        return [
          ...keywordCompletions(),
          ...typeCompletions(),
          ...builtinCompletions(),
          ...booleanCompletions(),
          ...snippetCompletions(),
        ];
      },
    }
  );

  context.subscriptions.push(provider);
}

function deactivate() {}

module.exports = { activate, deactivate };
