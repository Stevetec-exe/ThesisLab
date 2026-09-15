package de.stevetec.operaton_container.amqp_connector;

import org.operaton.bpm.engine.delegate.BpmnError;
import org.operaton.connect.impl.AbstractConnector;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.ConnectionFactory;

import de.stevetec.operaton_container.amqp.AMQPClient;
import de.stevetec.operaton_container.amqp.AMQPClientProvider;
import de.stevetec.operaton_container.amqp.ConnectionManager;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeoutException;

public class AMQPConnector extends AbstractConnector<AMQPRequest, AMQPResponse> {

    public static final String ID = "amqp-connector";


    public AMQPConnector() throws IOException, TimeoutException {
        super(ID);
    }

    @Override
    public AMQPRequest createRequest() {
        return new AMQPRequest(this);
    }

    @Override
    public AMQPResponse execute(AMQPRequest request) {
        ObjectMapper objectMapper = new ObjectMapper();
        String jsonString;
        try {
            jsonString = objectMapper.writeValueAsString(request.getVariables().asValueMap());
        } catch (JsonProcessingException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
            jsonString = "{\"error\":\"Error in object mapper\"}";
        }

        String providerName = request.getProvider();
        String targetQueue = request.getQueue();

        try {
            ConnectionManager p = AMQPClientProvider.getProvider(providerName);
            if(p != null){
                p.getClient().publish(targetQueue, jsonString);
            }else{
                System.out.println(String.format("[AMQP] Provider '%s' not available",providerName));
            }
        } catch (IOException e) {
            // TODO Auto-generated catch block
            System.out.println("[AMQP] ERROR in execution");
            e.printStackTrace();
        }

        AMQPResponse response = new AMQPResponse();
        response.setResponse("NOT_IMPLEMENTED");
        return response;
    }
}
