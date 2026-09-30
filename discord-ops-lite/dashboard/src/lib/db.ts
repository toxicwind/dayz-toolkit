import mysql from 'mysql2/promise';

export const dbRequest = async (query: string, values: any[] = []) => {
    const connection = await mysql.createConnection({
        host: process.env.DAYZ_MYSQL_HOST || 'mysql',
        user: process.env.DAYZ_MYSQL_USER,
        password: process.env.DAYZ_MYSQL_PASS,
        database: process.env.DAYZ_MYSQL_DB,
        port: parseInt(process.env.DAYZ_MYSQL_PORT || '3306'),
    });

    try {
        const [results] = await connection.execute(query, values);
        return results;
    } finally {
        await connection.end();
    }
};
