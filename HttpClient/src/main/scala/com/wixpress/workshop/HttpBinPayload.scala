package com.wixpress.workshop

case class HttpBinPayload(url: String,
                          args: Map[String, String],
                          headers: Map[String, String],
                          origin: String,
                          id: Int
                         )
