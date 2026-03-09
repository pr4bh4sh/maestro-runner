/** @type {import('ts-jest').JestConfigWithTsJest} */
module.exports = {
  preset: "ts-jest",
  testEnvironment: "node",
  roots: ["<rootDir>/tests"],
  testTimeout: 120_000,
  reporters: [
    "default",
    [
      "jest-html-reporters",
      {
        publicPath: "./reports",
        filename: "report.html",
        pageTitle: "maestro-runner TypeScript Test Report",
        expand: true,
      },
    ],
    [
      "jest-junit",
      {
        outputDirectory: "./reports",
        outputName: "junit-report.xml",
      },
    ],
  ],
};
