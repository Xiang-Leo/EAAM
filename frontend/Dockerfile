FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm config set registry https://registry.npmmirror.com && npm install

COPY . .

RUN npm run build

CMD ["npm", "start"]
