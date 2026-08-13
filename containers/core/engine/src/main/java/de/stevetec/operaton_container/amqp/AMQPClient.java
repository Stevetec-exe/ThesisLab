package de.stevetec.operaton_container.amqp;

import org.operaton.bpm.engine.delegate.BpmnError;
import org.operaton.connect.impl.AbstractConnector;

import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.ConnectionFactory;
import com.rabbitmq.client.DeliverCallback;

import de.stevetec.operaton_container.amqp_connector.AMQPConnector;
import de.stevetec.operaton_container.amqp_connector.AMQPRequest;
import de.stevetec.operaton_container.amqp_connector.AMQPResponse;

import java.io.IOException;
import java.net.ConnectException;
import java.net.URISyntaxException;
import java.nio.charset.StandardCharsets;
import java.security.KeyManagementException;
import java.security.NoSuchAlgorithmException;
import java.util.Map;
import java.util.concurrent.TimeoutException;

public class AMQPClient {
    private final static String[] QUEUES = {
            "amqp-connector-engine", // Inbound to engine
            "amqp-connector-services" // Outbound to world
    };

    private ConnectionFactory factory;
    private Connection connection;
    private Channel channel;

    private String connectionString;

    private boolean connected = false;

    public AMQPClient(String connectionString){
        System.out.println("[AMQP] Creating AMQPClient");
        this.connectionString = connectionString;
    }

    public void init() {
        try{
            // if the target is null we stay disconnected.
            if(this.connectionString == null){
                System.out.println("[AMQP] WARN no broker URI configured. skipping initialization");
                return;
            }
            this.factory = new ConnectionFactory();
            this.factory.setUri(this.connectionString);
    
            this.connection = this.factory.newConnection();
            this.channel = this.connection.createChannel();
    
            // Declare all queues
            for (int i = 0; i < QUEUES.length; i++) {
                this.channel.queueDeclare(QUEUES[i], true, false, false, Map.of("x-queue-type", "quorum"));
            }

            this.connected = true;
        }catch(IOException | TimeoutException | KeyManagementException | NoSuchAlgorithmException | URISyntaxException e){
            this.connected = false;
            System.out.println(String.format("[AMQP] could not initialize broker connection: %s",e.getMessage()));
        }
    }

    public Channel getChannel() {
        return this.channel;
    }

    public String getConnectionString(){
        return this.connectionString;
    }

    public boolean isConnected(){
        return this.connected;
    }

    /**
     * Push a string message to an AMQP queue
     * 
     * @param target  Name of the queue to emit to
     * @param message Payload to publish onto the queue
     * 
     * @throws IOException Bubbles send channel errors, also throws an IOException
     *                     if the requested target queue is not predeclared.
     */
    public void publish(String target, String message) throws IOException {
        // check for valid target
        boolean isValid = false;
        for (int i = 0; i < QUEUES.length; i++) {
            if (QUEUES[i] == target) {
                isValid = true;
                break;
            }
        }
        if (!isValid) {
            throw new IOException(String.format("Invalid publish target '%s': Queue not found.", target));
        }
        if(!this.isConnected()){
            System.out.print(String.format("[AMQP] broker connection not established, cannot send to <%s>: %s",target,message));
            return;
        }
        Channel c = this.getChannel();
        c.basicPublish("", target, null, message.getBytes(StandardCharsets.UTF_8));
    }

    public void registerCallback(String target, DeliverCallback callback) throws IOException{

        // check for valid target
        boolean isValid = false;
        for (int i = 0; i < QUEUES.length; i++) {
            if (QUEUES[i] == target) {
                isValid = true;
                break;
            }
        }
        if (!isValid) {
            throw new IOException(String.format("Invalid publish target '%s': Queue not found.", target));
        }

        if(!this.isConnected()){
            System.out.print(String.format("[AMQP] broker connection not established, cannot attach callback to <%s>",target));
            return;
        }
        Channel c = this.getChannel();
        c.basicConsume(target, true, callback, consumerTag -> { });
    }
}
