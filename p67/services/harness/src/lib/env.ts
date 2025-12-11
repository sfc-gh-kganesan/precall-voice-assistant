export const getDataRoot = (): string | null => {
  return process.env.DATA_ROOT || null;
};

export const getPort = (): number => {
  return process.env.PORT ? Number.parseInt(process.env.PORT) : 3000;
};
