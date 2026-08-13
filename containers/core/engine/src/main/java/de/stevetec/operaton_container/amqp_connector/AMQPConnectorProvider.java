package de.stevetec.operaton_container.amqp_connector;

import java.io.IOException;
import java.util.concurrent.TimeoutException;

import org.operaton.connect.spi.Connector;
import org.operaton.connect.spi.ConnectorProvider;

public class AMQPConnectorProvider implements ConnectorProvider {

    @Override
    public String getConnectorId() {
        return AMQPConnector.ID;
    }

    @Override
    public Connector<?> createConnectorInstance() {
        System.out.println("[AMQP] connector instance created");
        AMQPConnector instance = null;
        try {
            instance = new AMQPConnector();
        } catch (IOException | TimeoutException e) {
            // TODO Auto-generated catch block
            System.out.println("[AMQP] Fatal error in connector setup");
            e.printStackTrace();
            System.exit(-1);
            
        }
        return instance;
    }
}
