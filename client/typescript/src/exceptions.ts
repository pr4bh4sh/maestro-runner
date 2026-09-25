/** Custom exceptions for maestro-runner client. */

export class MaestroError extends Error {
  public readonly statusCode?: number;

  constructor(message: string, statusCode?: number) {
    super(message);
    this.name = "MaestroError";
    this.statusCode = statusCode;
  }
}

export class SessionError extends MaestroError {
  constructor(message: string, statusCode?: number) {
    super(message, statusCode);
    this.name = "SessionError";
  }
}

export class StepError extends MaestroError {
  constructor(message: string, statusCode?: number) {
    super(message, statusCode);
    this.name = "StepError";
  }
}
