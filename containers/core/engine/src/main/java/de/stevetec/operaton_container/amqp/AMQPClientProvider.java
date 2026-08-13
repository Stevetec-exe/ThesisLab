package de.stevetec.operaton_container.amqp;

import java.util.HashMap;
import java.util.Map;

public class AMQPClientProvider {

    private static Map<String, ConnectionManager> connectionManagerMap = new HashMap<String, ConnectionManager>();

    public static ConnectionManager getProvider(String name){
        return connectionManagerMap.get(name);
    }

    public static void createProvider(String key,String connectionURI){
        ConnectionManager mng = new ConnectionManager(connectionURI);
        AMQPClientProvider.connectionManagerMap.put(key, mng);
    }
}
