import { createContext } from 'react';

// Determines if a grid is an inner grid or not
// Inner grids default to not having margin
const GridContext = createContext<boolean>(false);

export { GridContext };
