"use strict";

const js = require("@eslint/js");

module.exports = [
  {ignores: ["node_modules/**"]},
  js.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "commonjs",
      globals: {
        require: "readonly",
        module: "readonly",
        exports: "writable",
        process: "readonly",
        console: "readonly",
        __dirname: "readonly",
      },
    },
    rules: {
      "no-unused-vars": ["error", {argsIgnorePattern: "^_"}],
    },
  },
];
