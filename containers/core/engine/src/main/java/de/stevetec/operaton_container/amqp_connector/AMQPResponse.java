package de.stevetec.operaton_container.amqp_connector;

import org.operaton.connect.impl.AbstractConnectorResponse;

import java.util.Map;

public class AMQPResponse extends AbstractConnectorResponse {

    private String response;

    public String getResponse() {
        return response;
    }

    public void setResponse(String value) {
        this.response = value;
    }

    @Override
    protected void collectResponseParameters(Map<String, Object> responseParameters) {
        if (response != null) {
            responseParameters.put("response", response);
        }
    }
}
