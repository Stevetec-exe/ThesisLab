package de.stevetec.operaton_container.amqp_connector;

import org.operaton.bpm.engine.variable.impl.VariableMapImpl;
import org.operaton.connect.impl.AbstractConnectorRequest;
import org.operaton.connect.spi.Connector;
import org.operaton.connect.spi.ConnectorRequest;

public class AMQPRequest extends AbstractConnectorRequest<AMQPResponse> {

    public static String DEFAULT_PROVIDER_NAME = "rabbit";
    public static String DEFAULT_QUEUE_NAME = "amqp-connector-services";

    @SuppressWarnings("unchecked")
    public AMQPRequest(Connector<AMQPRequest> connector) {
        super((Connector<ConnectorRequest<AMQPResponse>>) (Connector<?>) connector);
    }

    public String getMessage() {
        return (String) getRequestParameter("message");
    }

    public VariableMapImpl getVariables(){
        return getRequestParameter("variables");
    }

    public String getProvider(){
        String provider = (String) getRequestParameter("provider");
        if(provider == null){
            provider = AMQPRequest.DEFAULT_PROVIDER_NAME;
        }
        return provider.toString();
    }

    public String getQueue(){
        String provider = (String) getRequestParameter("queue");
        if(provider == null){
            provider = AMQPRequest.DEFAULT_QUEUE_NAME;
        }
        return provider.toString();
    }

    @Override
    protected boolean isRequestValid() {
        return true;
    }
}


