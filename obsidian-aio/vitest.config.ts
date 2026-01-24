import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  resolve: {
    alias: {
      // Mock the obsidian module to avoid resolution errors
      obsidian: path.resolve(__dirname, 'tests/mocks/obsidian-module.ts'),
    },
  },
  test: {
    globals: true,
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.ts'],
      exclude: ['src/main.ts'],
    },
    reporters: ['default', 'json'],
    outputFile: {
      json: '../test-results/typescript-results.json',
    },
  },
});
