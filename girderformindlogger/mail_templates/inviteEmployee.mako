<%include file="_header.mako"/>

<p>
    Hello ${userName}!
</p>

<p>
    You were invited by ${coordinatorName} to be a ${role} of ${appletName} applet on MindLogger. 
</p>

<p>
    <a href="${url}/accept" style="padding: 0.28rem 0.64rem; font-size: 0.8rem; line-height: 1.5; border-radius: 0.3rem; margin: 4px; display: inline-block; font-weight: 400; text-align: center; vertical-align: middle; text-decoration: none; color: #ffffff; background-color: rgb(0, 187, 133); border-color: rgb(0, 187, 133);">Accept Invitation</a> 
    <a href="${url}/decline" style="padding: 0.28rem 0.64rem; font-size: 0.8rem; line-height: 1.5; border-radius: 0.3rem; margin: 4px; display: inline-block; font-weight: 400; text-align: center; vertical-align: middle; text-decoration: none; color: #ffffff; background-color: rgb(255, 0, 69); border-color: rgb(255, 0, 69);">Decline Invitation</a>
</p>

<%include file="_footer.mako"/>
