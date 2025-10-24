import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import reactPlugin from 'eslint-plugin-react';
import reactHooksPlugin from 'eslint-plugin-react-hooks';

export default tseslint.config(
  // Ignore patterns
  {
    ignores: ['node_modules', 'build', 'dist', '.vite', 'vite.config.ts'],
  },

  // Base JavaScript recommended rules
  js.configs.recommended,

  // TypeScript recommended rules
  ...tseslint.configs.recommended,

  // Allow require() in plain .js files (like server.js)
  {
    files: ['**/*.js'],
    rules: {
      '@typescript-eslint/no-require-imports': 'off',
    },
  },

  // Custom minimal rule set (similar to Python's E4, E7, E9, F)
  {
    files: ['**/*.{js,jsx,ts,tsx}'],
    plugins: {
      react: reactPlugin,
      'react-hooks': reactHooksPlugin,
    },
    languageOptions: {
      globals: {
        // Browser globals
        console: 'readonly',
        document: 'readonly',
        window: 'readonly',
        setTimeout: 'readonly',
        fetch: 'readonly',
        URLSearchParams: 'readonly',
        HTMLElement: 'readonly',
        HTMLDivElement: 'readonly',
        HTMLImageElement: 'readonly',
        HTMLInputElement: 'readonly',
        KeyboardEvent: 'readonly',
        React: 'readonly',
        // Node.js globals (for server.js)
        require: 'readonly',
        process: 'readonly',
        __dirname: 'readonly',
        module: 'readonly',
        exports: 'readonly',
      },
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    rules: {
      // ===== Core Error Detection (like Python F rules) =====
      'no-undef': 'error', // Catch undefined variables
      'no-unused-vars': 'off', // Turn off base rule
      '@typescript-eslint/no-unused-vars': [
        'warn',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
      'no-unreachable': 'error', // Dead code detection
      'no-const-assign': 'error', // Catch const reassignment
      'no-dupe-keys': 'error', // Duplicate object keys
      'no-duplicate-case': 'error', // Duplicate case labels
      'no-func-assign': 'error', // Function reassignment
      'no-import-assign': 'error', // Import reassignment
      'no-redeclare': 'error', // Variable redeclaration

      // ===== React Specific Errors =====
      'react/jsx-key': 'error', // Missing key in lists
      'react/jsx-no-duplicate-props': 'error', // Duplicate props
      'react/jsx-no-undef': 'error', // Undefined components
      'react/jsx-uses-vars': 'error', // Mark JSX variables as used
      'react/no-children-prop': 'error', // Don't use children as prop
      'react/no-direct-mutation-state': 'error', // Don't mutate state
      'react/no-unescaped-entities': 'warn', // Escape entities in JSX

      // ===== React Hooks Rules =====
      'react-hooks/rules-of-hooks': 'error', // Check hook rules
      'react-hooks/exhaustive-deps': 'warn', // Check effect dependencies

      // ===== TypeScript Specific =====
      '@typescript-eslint/no-explicit-any': 'off', // Allow any (for flexibility)
      '@typescript-eslint/explicit-module-boundary-types': 'off', // No forced return types
      '@typescript-eslint/no-non-null-assertion': 'warn', // Warn on ! operator

      // ===== Turn off style/formatting rules (not our concern) =====
      'no-mixed-spaces-and-tabs': 'off',
      indent: 'off',
      quotes: 'off',
      semi: 'off',
      'comma-dangle': 'off',
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
  }
);

